# -*- coding: utf-8 -*-
"""Asynchroniczny klient modeli językowych.

Zapytania idą przez QgsNetworkAccessManager, więc respektują ustawienia proxy
i certyfikatów QGIS, a interfejs nie zamarza podczas oczekiwania na odpowiedź.
Klucz API jest wysyłany wyłącznie w nagłówku do adresu dostawcy wybranego
w ustawieniach – nigdzie indziej i nigdy nie trafia do logów.

Anthropic działa tak jak w Asystencie AI geoportalu: długi prompt systemowy
jest oznaczony do cache'owania (niższy koszt kolejnych zapytań), model może
użyć narzędzia web_search (wyszukiwania wykonuje API Anthropic), a przy
długiej turze z wyszukiwaniem („pause_turn”) odpowiedź jest przekazywana
z powrotem, żeby model ją dokończył.
"""
import json

from qgis.core import QgsNetworkAccessManager
from qgis.PyQt.QtCore import QByteArray, QObject, QTimer, QUrl, pyqtSignal
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

from .constants import LLM_MAX_CONTINUATIONS, OLLAMA_TEMPERATURE
from .stream import StreamParser
from .utils import redact_key
from .i18n import tr


def _extend_qgis_timeout(reply, ms):
    """Wydłuż limit bezczynności menedżera sieci QGIS dla zapytania.

    Menedżer sieci QGIS przerywa zapytanie po własnym limicie (Opcje › Sieć,
    domyślnie 60 s), liczonym do pierwszego bajtu odpowiedzi. Model może
    myśleć dłużej (np. Ollama na CPU), więc wydłużamy ten limit do wartości
    wtyczki. Strumieniowanie dodatkowo odnawia go z każdym fragmentem.
    """
    try:
        timer = reply.findChild(QTimer, "timeoutTimer")
        if timer is not None and 0 < timer.interval() < ms:
            timer.setInterval(ms)
            timer.start()
    # brak timera w danej wersji QGIS nie jest błędem
    except Exception:  # noqa: BLE001
        pass


class LLMClient(QObject):
    """Wysyła zapytanie do modelu i zgłasza wynik sygnałami."""

    finished = pyqtSignal(str)   # surowy tekst odpowiedzi modelu
    failed = pyqtSignal(str)     # komunikat błędu (bez sekretów)
    # liczba odebranych znaków (odpowiedź strumieniowa)
    progress = pyqtSignal(int)
    # model wyszukuje w internecie (treść zapytania)
    searching = pyqtSignal(str)
    # informacja dla dziennika (np. wyszukiwanie niedostępne)
    notice = pyqtSignal(str)

    # Parametry, których dany model nie przyjmuje – uczymy się tego
    # z odpowiedzi API (HTTP 400) i przy kolejnych zapytaniach od razu
    # wysyłamy poprawną wersję.
    # np. nowsze modele Claude, modele rozumujące OpenAI
    _no_temperature = set()
    # OpenAI: max_completion_tokens zamiast max_tokens
    _completion_tokens = set()
    # serwery zgodne z API, które nie obsługują strumieniowania
    _no_stream = set()
    # klucze/organizacje bez włączonego wyszukiwania (Claude Console)
    _no_web_search = set()

    def __init__(self, parent=None):
        """Utwórz klienta (bez trwającego zapytania)."""
        super().__init__(parent)
        self._reply = None
        self._aborted = False
        self._config = None
        self._request_args = None
        self._fixes = set()
        self._continuations = 0
        # tekst z wcześniejszych części tury (przed „pause_turn”)
        self._prior_text = ""
        self._turn_messages = []
        self._raw = bytearray()
        self._streamed = False
        self._parser = None          # StreamParser bieżącego zapytania

    @staticmethod
    def web_search_available(cfg):
        """Czy w zapytaniu będzie narzędzie web_search.

        Używane także do opisu kontekstu dla modelu.
        """
        return bool(cfg and cfg.get("provider") == "anthropic"
                    and cfg.get("web_search")
                    and LLMClient._model_key(cfg)
                    not in LLMClient._no_web_search)

    def abort(self):
        """Przerwij trwające zapytanie (bez sygnału failed)."""
        if self._reply is not None:
            self._aborted = True
            self._reply.abort()

    # ----------------------------------------------------------------- wysyłka
    def request(self, system, messages, config):
        """Wyślij zapytanie; poprzednie, jeśli trwa, zostaje przerwane.

        messages: lista {"role": "user"|"assistant", "content": str}.
        """
        if self._reply is not None:
            self.abort()
        self._aborted = False
        self._config = config
        self._request_args = (system, list(messages))
        # każda automatyczna poprawka parametrów – najwyżej raz na zapytanie
        self._fixes = set()
        self._restart()

    def _restart(self):
        """Zacznij zapytanie od początku.

        Pierwsze albo ponowione po poprawce parametrów.
        """
        self._continuations = 0
        self._prior_text = ""
        self._turn_messages = list(self._request_args[1])
        self._send()

    def _send(self):
        system = self._request_args[0]
        messages = self._turn_messages
        config = self._config
        provider = config["provider"]
        secret = config.get("api_key", "")
        if provider != "ollama" and not secret:
            self.failed.emit(tr("Brak klucza API – uzupełnij go w "
                                "ustawieniach wtyczki (ikona ⚙)."))
            return
        try:
            url, headers, body = getattr(self, "_build_" + provider)(
                system, messages, config)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(tr("Nie udało się przygotować zapytania: %s")
                             % redact_key(str(e), secret))
            return

        req = QNetworkRequest(QUrl(url))
        req.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader,
                      "application/json")
        for k, v in headers.items():
            req.setRawHeader(k.encode("ascii"), v.encode("utf-8"))
        timeout_ms = int(config.get("timeout_s", 120)) * 1000
        # limit bezczynności – przy strumieniowaniu każdy fragment odpowiedzi
        # go odnawia
        req.setTransferTimeout(timeout_ms)
        self._raw = bytearray()
        self._streamed = False
        # tekst, bloki (wznowienie tury), wyszukiwania, stop_reason
        self._parser = StreamParser(provider)
        payload = QByteArray(
            json.dumps(body, ensure_ascii=False).encode("utf-8"))
        reply = QgsNetworkAccessManager.instance().post(req, payload)
        self._reply = reply
        _extend_qgis_timeout(reply, timeout_ms)
        # obiekt reply przekazujemy jawnie – odpowiedź z przerwanego zapytania
        # nie pomyli się z nową
        reply.readyRead.connect(lambda r=reply: self._on_ready(r))
        reply.finished.connect(lambda r=reply: self._on_finished(r))

    # ------------------------------------------------------------- formaty API
    @staticmethod
    def _model_key(cfg):
        return (cfg.get("provider"), cfg.get("endpoint"), cfg.get("model"))

    @staticmethod
    def _add_temperature(body, cfg):
        if (cfg.get("temperature") is None
                or LLMClient._model_key(cfg) in LLMClient._no_temperature):
            return
        body["temperature"] = float(cfg["temperature"])

    @staticmethod
    def _stream(cfg):
        return LLMClient._model_key(cfg) not in LLMClient._no_stream

    @staticmethod
    def _max_tokens(cfg):
        return int(cfg.get("max_tokens", 4096))

    @staticmethod
    def _build_anthropic(system, messages, cfg):
        body = {
            "model": cfg["model"],
            "max_tokens": LLMClient._max_tokens(cfg),
            # długi prompt systemowy w pamięci podręcznej API – kolejne
            # zapytania są tańsze i szybsze
            "system": [{"type": "text", "text": system,
                        "cache_control": {"type": "ephemeral"}}],
            "messages": messages,
        }
        if LLMClient._stream(cfg):
            body["stream"] = True
        if LLMClient.web_search_available(cfg):
            body["tools"] = [{
                "type": "web_search_20250305", "name": "web_search",
                "max_uses": int(cfg.get("web_search_max_uses") or 4)}]
        LLMClient._add_temperature(body, cfg)
        headers = {"x-api-key": cfg["api_key"],
                   "anthropic-version": "2023-06-01"}
        if cfg.get("workspace_id"):
            headers["anthropic-workspace-id"] = cfg["workspace_id"]
        return cfg["endpoint"], headers, body

    @staticmethod
    def _build_openai(system, messages, cfg):
        tokens_key = ("max_completion_tokens"
                      if LLMClient._model_key(cfg)
                      in LLMClient._completion_tokens
                      else "max_tokens")
        body = {
            "model": cfg["model"],
            tokens_key: LLMClient._max_tokens(cfg),
            "messages": [{"role": "system", "content": system}] + messages,
        }
        if LLMClient._stream(cfg):
            body["stream"] = True
        LLMClient._add_temperature(body, cfg)
        if "api.openai.com" in cfg["endpoint"]:
            body["response_format"] = {"type": "json_object"}
        headers = {"Authorization": "Bearer " + cfg["api_key"]}
        return cfg["endpoint"], headers, body

    @staticmethod
    def _build_ollama(system, messages, cfg):
        temperature = cfg.get("temperature")
        body = {
            "model": cfg["model"],
            "stream": LLMClient._stream(cfg),
            "format": "json",
            "options": {"temperature": float(temperature
                                             if temperature is not None
                                             else OLLAMA_TEMPERATURE),
                        "num_predict": LLMClient._max_tokens(cfg)},
            "messages": [{"role": "system", "content": system}] + messages,
        }
        return cfg["endpoint"], {}, body

    # -------------------------------------------------- odpowiedź strumieniowa
    def _on_ready(self, reply):
        if reply is not self._reply:
            return
        chunk = bytes(reply.readAll())
        self._raw.extend(chunk)
        status = reply.attribute(
            QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        ctype = str(reply.header(
            QNetworkRequest.KnownHeaders.ContentTypeHeader) or "").lower()
        if ((status and int(status) >= 400)
                or not ("event-stream" in ctype or "ndjson" in ctype)):
            # błąd lub zwykły JSON – całość interpretujemy po zakończeniu
            return
        self._streamed = True
        for query in self._parser.feed(chunk):
            self.searching.emit(query)
        self.progress.emit(len(self._prior_text) + self._parser.chars())

    def _continue_turn(self, text):
        """Przekaż odpowiedź modelowi do dokończenia („pause_turn”).

        Model nie skończył tury (długie wyszukiwanie), więc odsyłamy mu jego
        dotychczasową odpowiedź.
        """
        if (self._continuations >= LLM_MAX_CONTINUATIONS
                or not self._parser.blocks):
            return False
        self._turn_messages = self._turn_messages + [
            {"role": "assistant",
             "content": self._parser.continuation_content()}]
        self._prior_text += text
        self._continuations += 1
        self._send()
        return True

    # ------------------------------------------------------------- zakończenie
    def _on_finished(self, reply):
        if reply is not self._reply:
            # odpowiedź z przerwanego lub zastąpionego zapytania
            reply.deleteLater()
            return
        self._reply = None
        secret = (self._config or {}).get("api_key", "")
        try:
            if self._aborted:
                return
            status = reply.attribute(
                QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            self._raw.extend(bytes(reply.readAll()))
            if self._streamed:
                self._parser.flush()
            raw = bytes(self._raw).decode("utf-8", "replace")
            if reply.error() != QNetworkReply.NetworkError.NoError:
                detail = self._api_error(raw) or reply.errorString()
                if self._retry_fixed(status, detail):
                    return
                self.failed.emit(redact_key(
                    self._error_message(reply, status, detail), secret))
                return
            if self._parser.error:
                self.failed.emit(redact_key(
                    self._api_failure(self._parser.error), secret))
                return
            try:
                if self._streamed:
                    text = self._parser.result_text()
                else:
                    text = self._parser.complete(raw)
                    for query in self._parser.searches:
                        self.searching.emit(query)
            except Exception as e:  # noqa: BLE001
                self.failed.emit(redact_key(
                    tr("Nieoczekiwany format odpowiedzi API: %s") % e,
                    secret))
                return
            if (self._parser.stop_reason == "pause_turn"
                    and self._continue_turn(text)):
                return
            self.finished.emit(self._prior_text + text)
        finally:
            reply.deleteLater()

    def _retry_fixed(self, status, detail):
        """Ponów raz zapytanie po odrzuceniu parametru (HTTP 400).

        Poprawka jest zapamiętywana dla modelu na kolejne zapytania.
        """
        if status != 400:
            return False
        low = (detail or "").lower()
        key = self._model_key(self._config)
        if ("temperature" in low and key not in LLMClient._no_temperature
                and "temperature" not in self._fixes):
            LLMClient._no_temperature.add(key)
            fix = "temperature"
        elif ("max_tokens" in low and "max_completion_tokens" in low
              and "tokens" not in self._fixes):
            # OpenAI: modele rozumujące wymagają max_completion_tokens,
            # starsze serwery – max_tokens
            LLMClient._completion_tokens.symmetric_difference_update({key})
            fix = "tokens"
        elif (("web search" in low or "web_search" in low)
              and LLMClient.web_search_available(self._config)
              and "web_search" not in self._fixes):
            # wyszukiwanie nie jest włączone dla organizacji w Claude
            # Console – działamy bez niego
            LLMClient._no_web_search.add(key)
            fix = "web_search"
            self.notice.emit(tr("Wyszukiwanie w internecie jest niedostępne "
                                "dla tego klucza API (administrator może je "
                                "włączyć w Claude Console › Settings › "
                                "Privacy) – asystent działa bez niego."))
        elif ("stream" in low and key not in LLMClient._no_stream
              and "stream" not in self._fixes):
            LLMClient._no_stream.add(key)
            fix = "stream"
        else:
            return False
        self._fixes.add(fix)
        self._restart()
        return True

    def _error_message(self, reply, status, detail):
        low = (detail or "").lower()
        hint = ""
        if status == 401:
            hint = tr(" – sprawdź klucz API w ustawieniach.")
        elif status == 403:
            hint = tr(" – klucz API nie ma uprawnień do tej operacji albo "
                      "modelu.")
        elif "credit balance" in low or "billing" in low:
            hint = tr(" – brak środków na koncie API. Doładuj konto u "
                      "dostawcy (np. Claude Console › Settings › Billing); "
                      "po wpłacie asystent zadziała bez zmian w "
                      "ustawieniach.")
        elif status == 404 or ("model" in low and (
                "not found" in low or "does not exist" in low)):
            hint = tr(" – model „%s” jest niedostępny dla tego klucza. "
                      "Wybierz inny model w ustawieniach wtyczki.") % (
                (self._config or {}).get("model", ""))
        elif ("prompt is too long" in low or "too many tokens" in low
              or "context length" in low):
            hint = tr(" – opis projektu jest zbyt długi dla modelu. Usuń "
                      "część warstw z projektu albo kliknij „Nowe "
                      "polecenie”.")
        elif status in (500, 502, 503, 529) or "overloaded" in low:
            hint = tr(" – serwery dostawcy są chwilowo przeciążone, spróbuj "
                      "ponownie za chwilę.")
        elif status == 400 and "workspace" in low:
            hint = (tr(" – ten klucz nie jest przypisany do workspace. Wpisz "
                       "ID workspace (wrkspc_…) w ustawieniach wtyczki albo "
                       "utwórz w Claude Console klucz przypisany do "
                       "workspace."))
        elif status == 429:
            hint = tr(" – przekroczony limit zapytań, spróbuj za chwilę.")
        elif (reply.error()
              == QNetworkReply.NetworkError.OperationCanceledError):
            # przerwanie nie przez użytkownika – minął limit czasu (wtyczki
            # lub sieci QGIS, większy z nich)
            hint = tr(" – serwer nie odpowiedział w wyznaczonym czasie "
                      "(%d s). Spróbuj ponownie lub wybierz szybszy model; "
                      "limit czasu sieci można też zwiększyć w Ustawienia › "
                      "Opcje › Sieć.") % max(
                int((self._config or {}).get("timeout_s", 120)),
                QgsNetworkAccessManager.timeout() // 1000)
        elif status is None:
            hint = tr(" – brak połączenia z serwerem (sieć/proxy/adres API).")
        return self._api_failure(detail, status, hint)

    @staticmethod
    def _api_failure(detail, status=None, hint=""):
        """Komunikat „Błąd API (HTTP n): szczegóły – wskazówka”.

        Status i wskazówka są opcjonalne.
        """
        return tr("Błąd API%s: %s%s") % (
            " (HTTP %s)" % status if status else "", detail, hint)

    @staticmethod
    def _api_error(raw):
        try:
            data = json.loads(raw)
        except ValueError:
            return raw[:300] if raw else ""
        if isinstance(data, list) and data and isinstance(data[0], dict):
            data = data[0]          # niektóre bramki zwracają tablicę błędów
        if isinstance(data, str):
            return data[:300]
        if not isinstance(data, dict):
            return raw[:300]
        err = data.get("error")
        if isinstance(err, dict):
            return err.get("message") or json.dumps(err)[:300]
        if isinstance(err, str):
            return err
        return ""
