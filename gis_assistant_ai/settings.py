# -*- coding: utf-8 -*-
"""Ustawienia wtyczki oraz bezpieczne przechowywanie klucza API.

Klucz API NIGDY nie jest zapisywany jawnym tekstem w QgsSettings (profilu
QGIS). Trafia do zaszyfrowanej bazy menedżera uwierzytelniania QGIS
(qgis-auth.db, chronionej hasłem głównym) albo – na życzenie – tylko do
pamięci na czas sesji.
"""
from qgis.core import QgsApplication, QgsMessageLog, QgsSettings, Qgis

from .constants import (DEFAULT_PROVIDER, LLM_MAX_TOKENS, LLM_TIMEOUT_S,
                        LOG_TAG, OLLAMA_TEMPERATURE, PROVIDERS,
                        SETTINGS_PREFIX, WEB_SEARCH_MAX_USES)
from .i18n import tr


class Settings:
    """Ustawienia wtyczki w profilu QGIS (prefiks SETTINGS_PREFIX)."""

    DEFAULTS = {
        "provider": DEFAULT_PROVIDER,
        "send_samples": False,
        # kod od modelu tylko po świadomym włączeniu (audyt B1)
        "allow_python": False,
        "show_details": False,
        # tylko Anthropic Claude – jak w Asystencie AI geoportalu
        "web_search": True,
    }

    def __init__(self):
        """Utwórz obiekt ustawień oparty na QgsSettings."""
        self._s = QgsSettings()

    # -- podstawowe
    def value(self, key, default=None, type_=None):
        """Wartość ustawienia przekształcona na typ type_.

        Bez default używana jest wartość z DEFAULTS; typ wynika z default,
        gdy nie podano go jawnie.
        """
        full = SETTINGS_PREFIX + key
        if default is None:
            default = self.DEFAULTS.get(key)
        if type_ is None and default is not None:
            type_ = type(default)
        try:
            if type_ is bool:
                v = self._s.value(full, default)
                if isinstance(v, str):
                    return v.lower() in ("true", "1", "yes")
                return bool(v)
            if type_ in (int, float, str):
                return type_(self._s.value(full, default))
        except (TypeError, ValueError):
            return default
        return self._s.value(full, default)

    def set_value(self, key, value):
        """Zapisz wartość ustawienia."""
        self._s.setValue(SETTINGS_PREFIX + key, value)

    # -- dostawca / model
    @property
    def provider(self):
        """Wybrany dostawca modeli (domyślny, gdy zapisany jest nieznany)."""
        p = self.value("provider", DEFAULT_PROVIDER, str)
        return p if p in PROVIDERS else DEFAULT_PROVIDER

    def model(self, provider=None):
        """Model wybrany dla dostawcy."""
        provider = provider or self.provider
        return self.value("model/" + provider,
                          PROVIDERS[provider]["models"][0], str)

    def endpoint(self, provider=None):
        """Adres API dostawcy."""
        provider = provider or self.provider
        return self.value("endpoint/" + provider, PROVIDERS[provider]["url"],
                          str)

    def workspace(self, provider=None):
        """ID workspace Anthropic (wrkspc_…) – identyfikator, nie sekret."""
        provider = provider or self.provider
        return self.value("workspace/" + provider, "", str).strip()

    def web_search(self, provider=None):
        """Czy model może wyszukiwać w internecie.

        Narzędzie web_search jest dostępne tylko w API Anthropic.
        """
        provider = provider or self.provider
        return provider == "anthropic" and self.value("web_search", True, bool)

    def llm_config(self):
        """Konfiguracja zapytania dla LLMClient (z kluczem API)."""
        p = self.provider
        return {
            "workspace_id": self.workspace(p) if p == "anthropic" else "",
            "provider": p,
            "model": self.model(p),
            "endpoint": self.endpoint(p),
            "api_key": (SecretStore.get(p) if PROVIDERS[p]["needs_key"]
                        else ""),
            # temperatury nie wysyłamy do modeli w chmurze – nowsze modele ją
            # odrzucają
            "temperature": OLLAMA_TEMPERATURE if p == "ollama" else None,
            "max_tokens": LLM_MAX_TOKENS,
            "timeout_s": LLM_TIMEOUT_S.get(p, 180),
            "web_search": self.web_search(p),
            "web_search_max_uses": WEB_SEARCH_MAX_USES,
        }


class SecretStore:
    """Klucze API: zaszyfrowany magazyn QGIS lub pamięć sesji."""

    _session = {}
    _KEY = "asystent_ai/api_key/%s"

    @classmethod
    def clear_session(cls):
        """Usuń klucze trzymane w pamięci (przy wyłączaniu wtyczki)."""
        cls._session.clear()

    @classmethod
    def _am(cls):
        try:
            am = QgsApplication.authManager()
            if am is None or am.isDisabled():
                return None
            return am
        except Exception:  # noqa: BLE001
            return None

    @classmethod
    def has(cls, provider):
        """Czy dla dostawcy jest zapisany klucz (w pamięci lub magazynie)."""
        if cls._session.get(provider):
            return True
        am = cls._am()
        if am is None:
            return False
        try:
            return bool(am.existsAuthSetting(cls._KEY % provider))
        except Exception:  # noqa: BLE001
            return False

    @classmethod
    def get(cls, provider):
        """Klucz API dostawcy albo pusty tekst."""
        if cls._session.get(provider):
            return cls._session[provider]
        am = cls._am()
        if am is None:
            return ""
        key = cls._KEY % provider
        try:
            if not am.existsAuthSetting(key):
                return ""
            # decrypt=True – QGIS poprosi o hasło główne, jeśli nie zostało
            # jeszcze podane
            val = am.authSetting(key, "", True)
            val = str(val or "")
            if val:
                # bez ponownego pytania w tej sesji
                cls._session[provider] = val
            return val
        except Exception as e:  # noqa: BLE001
            QgsMessageLog.logMessage(
                tr("Nie udało się odczytać klucza API: %s") % e, LOG_TAG,
                Qgis.MessageLevel.Warning)
            return ""

    @classmethod
    def set(cls, provider, secret, persist=True):
        """Zapisz klucz API; zwraca (ok, opis_miejsca)."""
        secret = (secret or "").strip()
        cls._session[provider] = secret
        if not persist:
            cls._remove_persistent(provider)
            return True, tr("tylko w pamięci (do zamknięcia QGIS)")
        am = cls._am()
        if am is None:
            return True, tr("tylko w pamięci – menedżer uwierzytelniania "
                            "QGIS jest niedostępny")
        # Gdy zapis się nie uda, usuwamy poprzednio zapisany klucz – inaczej
        # po restarcie QGIS wróciłby stary.
        try:
            if not am.setMasterPassword(True):
                cls._remove_persistent(provider)
                return True, tr("tylko w pamięci – nie podano hasła głównego "
                                "QGIS")
            if am.storeAuthSetting(cls._KEY % provider, secret, True):
                return True, tr("zaszyfrowany w menedżerze uwierzytelniania "
                                "QGIS")
        except Exception as e:  # noqa: BLE001
            QgsMessageLog.logMessage(
                tr("Nie udało się zapisać klucza API: %s") % e, LOG_TAG,
                Qgis.MessageLevel.Warning)
        cls._remove_persistent(provider)
        return True, tr("tylko w pamięci – zapis w menedżerze "
                        "uwierzytelniania nie powiódł się")

    @classmethod
    def delete(cls, provider):
        """Usuń klucz dostawcy z pamięci i z magazynu."""
        cls._session.pop(provider, None)
        cls._remove_persistent(provider)

    @classmethod
    def _remove_persistent(cls, provider):
        am = cls._am()
        if am is None:
            return
        try:
            key = cls._KEY % provider
            if am.existsAuthSetting(key):
                am.removeAuthSetting(key)
        except Exception:  # noqa: BLE001
            pass
