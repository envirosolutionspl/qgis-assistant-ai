# -*- coding: utf-8 -*-
"""Wykonywanie planu krok po kroku.

Algorytmy Processing uruchamiane są w tle (QgsProcessingAlgRunnerTask), więc QGIS
nie zamarza. Kroki wymagające użytkownika wstrzymują plan do potwierdzenia.

Jak w Asystencie AI geoportalu:
- krok „add_service” sam sprawdza usługę (GetCapabilities), dobiera warstwę po nazwie lub słowach z tytułu
  i dodaje ją do projektu,
- „load_layer” z adresem http(s) pobiera dane (GeoJSON, ZIP, GPKG, KML, GML, Overpass API) do katalogu
  tymczasowego Processing,
- kontrola wyniku: pusty wynik z niepustych danych zatrzymuje plan z ostrzeżeniem i diagnozą
  (sygnał stepWarning) zamiast ogłaszać sukces.
"""
import contextlib
import io
import ipaddress
import math
import os
import traceback
import uuid
import zipfile
from urllib.parse import urlencode, urlsplit

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsDataSourceUri,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsMapLayer,
    QgsMessageLog,
    QgsNetworkAccessManager,
    QgsProcessingAlgRunnerTask,
    QgsProcessingContext,
    QgsProcessingFeatureSourceDefinition,
    QgsProcessingFeedback,
    QgsProcessingUtils,
    QgsProject,
    QgsProviderRegistry,
    QgsRasterLayer,
    QgsRectangle,
    QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QObject, QTimer, QUrl, pyqtSignal
from qgis.PyQt.QtNetwork import QHostInfo, QNetworkReply, QNetworkRequest

from .constants import (BDOT10K_MAX_MB, DOWNLOAD_TIMEOUT_S, LOG_TAG, MAX_CAPS_MB, MAX_DOWNLOAD_MB,
                        OVERPASS_RETRY_WAITS_S, ULDK_LEVELS, ULDK_URL)
import qgis.core as _qcore

from . import services as svc
from .i18n import tr
from .llm_client import _extend_qgis_timeout
from .utils import resolve_refs, short_json


def _string_field_type():
    """Typ pola tekstowego zgodny z wersją: QgsField(QMetaType) istnieje dopiero od QGIS 3.38."""
    try:
        from qgis.PyQt.QtCore import QVariant
        if Qgis.QGIS_VERSION_INT < 33800:
            return QVariant.String
    except (ImportError, AttributeError):  # PyQt6 nie ma QVariant.String
        pass
    from qgis.PyQt.QtCore import QMetaType
    return QMetaType.Type.QString


_STRING_TYPE = _string_field_type()

PENDING, RUNNING, DONE, ERROR, WAITING, SKIPPED = "pending", "running", "done", "error", "waiting", "skipped"

# Dostawcy czytający pliki z dysku – wczytanie wymaga potwierdzenia użytkownika (audyt B2).
LOCAL_PROVIDERS = {"ogr", "gdal", "delimitedtext", "spatialite", "pdal", "mdal", "virtual", "postgres",
                   "mssql", "oracle", "hana"}

_LAYER_OUTPUT_CLASSES = tuple(getattr(_qcore, n) for n in (
    "QgsProcessingOutputVectorLayer", "QgsProcessingOutputRasterLayer", "QgsProcessingOutputMapLayer",
    "QgsProcessingOutputPointCloudLayer", "QgsProcessingOutputVectorTileLayer") if hasattr(_qcore, n))


class StepError(Exception):
    pass


def _flag(obj, new_path, old_name):
    """Zwraca flagę w nowej (Qgis.*) lub starej konwencji API."""
    try:
        cur = Qgis
        for part in new_path.split("."):
            cur = getattr(cur, part)
        return cur
    except AttributeError:
        return getattr(obj, old_name)


def _is_optional(param):
    from qgis.core import QgsProcessingParameterDefinition
    flag = _flag(QgsProcessingParameterDefinition, "ProcessingParameterFlag.Optional", "FlagOptional")
    return bool(param.flags() & flag)


def _no_threading(alg):
    from qgis.core import QgsProcessingAlgorithm
    flag = _flag(QgsProcessingAlgorithm, "ProcessingAlgorithmFlag.NoThreading", "FlagNoThreading")
    return bool(alg.flags() & flag)


class _Feedback(QgsProcessingFeedback):
    def __init__(self):
        super().__init__()
        self.messages = []

    def reportError(self, error, fatalError=False):  # noqa: N802,N803
        self.messages.append(str(error))
        super().reportError(error, fatalError)

    def pushWarning(self, warning):  # noqa: N802
        self.messages.append(str(warning))
        super().pushWarning(warning)


class PlanExecutor(QObject):
    changed = pyqtSignal()                 # zmiana statusu kroków – odśwież widok
    log = pyqtSignal(str, str)             # poziom, komunikat
    statusText = pyqtSignal(str)           # tekst do paska statusu (np. odliczanie do ponowienia)
    progress = pyqtSignal(float)           # postęp bieżącego algorytmu 0–100
    waitingForUser = pyqtSignal(int)       # krok user_action czeka na użytkownika
    confirmPython = pyqtSignal(int)        # krok python czeka na zatwierdzenie kodu
    confirmLoad = pyqtSignal(int, str)     # wczytanie pliku lokalnego czeka na zatwierdzenie
    stepFailed = pyqtSignal(int, str)      # krok zakończył się błędem
    stepWarning = pyqtSignal(int, str)     # wynik kroku podejrzany (np. pusty) – plan czeka na decyzję
    replanRequested = pyqtSignal(int)      # po kroku użytkownika należy dopasować plan
    finished = pyqtSignal(bool)            # True = wszystko wykonane

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.plan = None
        self.steps = []
        self.idx = -1
        self.results = {}
        self.running = False
        self._task_refs = None
        self._net_reply = None
        self._uldk_queue = []
        self._uldk_layer = None
        # Numer bieżącego uruchomienia – spóźnione odpowiedzi z poprzedniego (np. po „Zatrzymaj”)
        # są ignorowane i nie przesuwają nowego planu (audyt A2).
        self._run_id = 0
        self._confirmed_loads = set()  # indeksy kroków load_layer zatwierdzonych w tym uruchomieniu
        self._dns_lookup = None        # id trwającego zapytania QHostInfo (kontrola adresu w sieci wewnętrznej)
        self._countdown = None         # QTimer odliczania do automatycznego ponowienia (Overpass)
        self._bdot_cache = {}          # TERYT powiatu → pobrana paczka BDOT10k (ZIP w katalogu tymczasowym)

    # ================================================================ sterowanie
    def start(self, plan):
        self.plan = plan
        self.steps = plan["steps"]
        for s in self.steps:
            s["_status"] = PENDING
            s.pop("_error", None)
            s.pop("_result_text", None)
            s.pop("_warning", None)
            _reset_overpass(s)
        self.results = {}
        self.idx = 0
        self.running = True
        self._run_id += 1
        self._task_refs = None
        self._net_reply = None
        self._confirmed_loads = set()
        self.log.emit("info", tr("Rozpoczynam wykonywanie planu „%s”.") % (plan.get("title") or ""))
        self._schedule()

    def abort(self):
        if not self.running:
            return
        self.running = False
        self._run_id += 1
        refs, self._task_refs = self._task_refs, None
        if refs:
            for obj in (refs[2], refs[3]):  # feedback i samo zadanie
                try:
                    obj.cancel()
                except Exception:  # noqa: BLE001
                    pass
        reply, self._net_reply = self._net_reply, None
        if reply is not None:
            reply.abort()
        self._abort_lookup()
        self._stop_countdown()
        if 0 <= self.idx < len(self.steps) and self.steps[self.idx]["_status"] in (RUNNING, WAITING):
            self.steps[self.idx]["_status"] = PENDING
        self.log.emit("warning", tr("Wykonywanie planu przerwane przez użytkownika."))
        self.changed.emit()
        self.finished.emit(False)

    def current(self):
        return self.steps[self.idx] if 0 <= self.idx < len(self.steps) else None

    def user_done(self, layer=None):
        """Użytkownik potwierdził wykonanie kroku user_action."""
        step = self.current()
        if not step or step["_status"] != WAITING:
            return
        exp = step.get("expects_layer")
        if layer is not None:
            self.results[step["id"]] = {"OUTPUT": layer.id(), "_layer_name": layer.name()}
            step["_result_text"] = tr("Wskazana warstwa: %s") % layer.name()
        elif exp:
            self.log.emit("warning", tr("Nie wskazano warstwy – kolejne kroki mogą jej wymagać."))
        self._mark(step, DONE)
        if step.get("replan_after"):
            self.replanRequested.emit(self.idx)   # interfejs wywoła apply_revision / continue_plan
        else:
            self._next()

    def skip(self):
        step = self.current()
        if not step:
            return
        self._mark(step, SKIPPED)
        self.log.emit("warning", tr("Pominięto krok: %s") % step["title"])
        self._next()

    def retry(self):
        step = self.current()
        if step:
            step.pop("_error", None)
            _reset_overpass(step)   # „Ponów” zaczyna od serwera głównego
            self._schedule()

    def continue_plan(self):
        """Kontynuacja po kroku użytkownika albo po ostrzeżeniu o wyniku – bez zmian planu."""
        self._next()

    def apply_revision(self, new_steps, from_index, continue_after=True):
        """Zastępuje kroki od from_index nowymi (np. po korekcie przez AI)."""
        self.steps[from_index:] = new_steps
        self._confirmed_loads = {i for i in self._confirmed_loads if i < from_index}
        self.plan["steps"] = self.steps
        self.log.emit("info", tr("Plan zaktualizowany (%d nowych kroków).") % len(new_steps))
        self.changed.emit()
        if continue_after:
            self.idx = from_index
            self._schedule()

    def done_summary(self):
        out = []
        for s in self.steps:
            if s["_status"] in (DONE, SKIPPED):
                res = self.results.get(s["id"], {})
                item = {"id": s["id"], "action": s["action"], "title": s["title"], "status": s["_status"]}
                layer_id = res.get("OUTPUT")
                lyr = QgsProject.instance().mapLayer(layer_id) if isinstance(layer_id, str) else None
                if lyr is not None:
                    item["output_layer"] = _layer_summary(lyr)
                else:
                    item["outputs"] = {k: v for k, v in res.items() if not k.startswith("_")}
                out.append(item)
        return out

    # ================================================================ pętla
    def _schedule(self):
        rid = self._run_id
        QTimer.singleShot(30, lambda r=rid: self._run_current(r))

    def _next(self):
        self.idx += 1
        self._schedule()

    def _mark(self, step, status):
        step["_status"] = status
        self.changed.emit()

    def _run_current(self, rid=None):
        if not self.running or (rid is not None and rid != self._run_id):
            return
        if self.idx >= len(self.steps):
            self.running = False
            self.log.emit("success", tr("Plan wykonany."))
            self.changed.emit()
            self.finished.emit(True)
            return
        step = self.steps[self.idx]
        self._mark(step, RUNNING)
        self.log.emit("info", tr("Krok %d: %s") % (self.idx + 1, step["title"]))
        handler = getattr(self, "_do_" + step["action"], None)
        try:
            if handler is None:
                raise StepError(tr("Nieobsługiwany typ kroku: %s") % step["action"])
            handler(step)
        except StepError as e:
            self._fail(step, str(e))
        except Exception as e:  # noqa: BLE001
            QgsMessageLog.logMessage(traceback.format_exc(), LOG_TAG, Qgis.MessageLevel.Critical)
            self._fail(step, "%s: %s" % (type(e).__name__, e))

    def _complete(self, step, result=None, text=None, warning=None):
        if not self.running:
            return
        self.results[step["id"]] = result or {}
        if text:
            step["_result_text"] = text
        if warning:
            # wynik podejrzany (np. pusty z niepustych danych) – nie ogłaszamy sukcesu, plan czeka na decyzję:
            # „Napraw z AI”, „Kontynuuj mimo to” (continue_plan) albo „Przerwij”
            step["_warning"] = warning
            self._mark(step, DONE)
            self.log.emit("warning", tr("Wynik kroku „%s” wymaga sprawdzenia: %s") % (step["title"], warning))
            self.stepWarning.emit(self.idx, warning)
            return
        self._mark(step, DONE)
        if step.get("replan_after") and step["action"] != "user_action":   # user_action obsługuje to w user_done()
            self.replanRequested.emit(self.idx)
            return
        self._next()

    def _fail(self, step, message):
        step["_error"] = message
        self._mark(step, ERROR)
        self.log.emit("error", tr("Błąd w kroku „%s”: %s") % (step["title"], message))
        self.stepFailed.emit(self.idx, message)

    # ================================================================ referencje
    def _lookup(self, sid, key):
        if sid not in self.results:
            raise StepError(tr("Krok „%s” nie ma jeszcze wyniku (pominięty lub nie wykonany).") % sid)
        res = self.results[sid]
        if key:
            if key not in res:
                raise StepError(tr("Krok „%s” nie ma wyjścia „%s” (dostępne: %s).") % (
                    sid, key, ", ".join(k for k in res if not k.startswith("_")) or "brak"))
            return res[key]
        if "OUTPUT" in res:
            return res["OUTPUT"]
        for v in res.values():
            if isinstance(v, str) and QgsProject.instance().mapLayer(v):
                return v
        raise StepError(tr("Krok „%s” nie zwrócił warstwy.") % sid)

    def _resolve(self, value):
        return resolve_refs(value, self._lookup)

    def get_layer(self, ref):
        ref = self._resolve(ref) if isinstance(ref, str) else ref
        if isinstance(ref, QgsMapLayer):
            return ref
        prj = QgsProject.instance()
        lyr = prj.mapLayer(str(ref))
        if lyr is None:
            found = prj.mapLayersByName(str(ref))
            lyr = found[0] if found else None
        return lyr

    # ================================================================ akcje
    # ---------------------------------------------------------------- processing
    def _do_processing(self, step):
        reg = QgsApplication.processingRegistry()
        alg = reg.createAlgorithmById(step["algorithm"])
        if alg is None:
            raise StepError(_unavailable_message(reg, step["algorithm"]))
        raw = dict(self._resolve(step.get("params") or {}))
        raw.update(step.get("_param_overrides") or {})   # np. serwer zapasowy Overpass po błędzie sieci
        params = self._prepare_params(alg, raw, step)
        if _is_quickosm(alg):
            step["_osm_server"] = str(params.get("SERVER") or svc.OVERPASS_SERVERS[0])

        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())
        context.setTransformContext(QgsProject.instance().transformContext())
        ec = QgsExpressionContext()
        ec.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(None))
        context.setExpressionContext(ec)
        feedback = _Feedback()
        feedback.progressChanged.connect(self.progress.emit)

        ok, msg = alg.checkParameterValues(params, context)
        if not ok:
            raise StepError(tr("Niepoprawne parametry: %s\nParametry: %s") % (msg, short_json(_printable(params))))
        self.log.emit("debug", "%s %s" % (step["algorithm"], short_json(_printable(params), 400)))
        _guard_assign_crs(step["algorithm"], params, self.get_layer)
        inputs = self._input_layers(params)   # stan wejść przed algorytmem – do kontroli pustego wyniku

        rid = self._run_id
        if _no_threading(alg):
            results, ok = alg.run(params, context, feedback)
            self._alg_done(step, alg, context, feedback, bool(ok), results or {}, rid, inputs)
            return
        task = QgsProcessingAlgRunnerTask(alg, params, context, feedback)
        self._task_refs = (alg, context, feedback, task)
        task.executed.connect(lambda ok, res, s=step, a=alg, c=context, f=feedback, r=rid, i=inputs:
                              self._alg_done(s, a, c, f, ok, res, r, i))
        QgsApplication.taskManager().addTask(task)

    def _prepare_params(self, alg, params, step):
        defs = {p.name(): p for p in alg.parameterDefinitions()}
        lower = {n.lower(): n for n in defs}
        clean = {}
        for k, v in params.items():
            name = k if k in defs else lower.get(str(k).lower())
            if not name:
                self.log.emit("warning", tr("Pomijam nieznany parametr „%s” algorytmu %s.") % (k, alg.id()))
                continue
            if isinstance(v, dict) and ("source" in v or "selected_only" in v):
                v = QgsProcessingFeatureSourceDefinition(str(v.get("source", "")), bool(v.get("selected_only")))
            if _is_optional(defs[name]) and _is_blank(v):
                continue  # pusty parametr opcjonalny – zostawiamy wartość domyślną algorytmu
            clean[name] = v
        for name, p in defs.items():
            if p.isDestination() and name not in clean and not _is_optional(p):
                clean[name] = "TEMPORARY_OUTPUT"
        fix = _PARAM_FIXES.get(alg.provider().id().lower() if alg.provider() else "")
        if fix:
            fix(clean, self.log)
        return clean

    def _alg_done(self, step, alg, context, feedback, ok, results, rid=None, inputs=None):
        if rid is not None and rid != self._run_id:
            return  # wynik zadania z przerwanego uruchomienia
        self._task_refs = None
        if not self.running or step is not self.current():
            return
        if not ok:
            detail = _clean_feedback(feedback.messages) or tr("Algorytm zakończył się niepowodzeniem.")
            if _is_quickosm(alg) and self._retry_overpass(step, alg, detail):
                return
            if _is_quickosm(alg) and svc.overpass_transient(detail):
                detail += "\n" + tr("Serwery Overpass API (OpenStreetMap) są teraz przeciążone – wtyczka przez "
                                    "ok. %d min ponawiała zapytanie na wszystkich serwerach zapasowych. To problem po "
                                    "stronie OpenStreetMap: kliknij „Ponów” za kilka minut.") % max(
                    1, round(sum(OVERPASS_RETRY_WAITS_S) / 60))
            self._fail(step, detail)
            return
        try:
            produced, texts = self._collect_outputs(step, alg, context, results)
        except Exception as e:  # noqa: BLE001
            self._fail(step, tr("Nie udało się dodać wyników do projektu: %s") % e)
            return
        warning = self._check_empty_result(inputs or [], produced)
        self._complete(step, produced, "; ".join(texts) if texts else None, warning)

    def _retry_overpass(self, step, alg, detail):
        """Błąd sieci Overpass w algorytmie QuickOSM: ponowienie na kolejnym serwerze bez angażowania AI.

        Ponawiamy przy przeciążeniu serwera (504, 429, 500, przekroczony czas) oraz gdy serwer wskazany przez model
        nie jest znaną instancją globalną (np. openstreetmap.fr odpowiada „Bad Request”)."""
        if "SERVER" not in {p.name() for p in alg.parameterDefinitions()}:
            return False
        failed = svc.overpass_server_in_error(detail) or step.get("_osm_server") or svc.OVERPASS_SERVERS[0]
        unknown = not svc.known_overpass_server(failed)
        if not svc.overpass_transient(detail) and not unknown:
            return False      # np. błąd zapytania albo limit pamięci – tu pomoże zmiana planu, nie serwera
        tried = step.setdefault("_osm_tried", [])
        tried.append(failed)
        nxt = svc.next_overpass_server(tried)
        if not nxt:
            return self._retry_overpass_later(step)
        step.setdefault("_param_overrides", {})["SERVER"] = nxt
        self.log.emit("warning", tr("Serwer Overpass %s nie odpowiedział poprawnie – ponawiam za chwilę na serwerze "
                                    "%s.") % (urlsplit(failed).hostname or failed, urlsplit(nxt).hostname))
        rid = self._run_id
        QTimer.singleShot(4000, lambda r=rid: self._run_current(r))
        return True

    def _retry_overpass_later(self, step):
        """Wszystkie serwery Overpass odpowiedziały błędem przeciążenia: kolejna runda po odczekaniu
        (OVERPASS_RETRY_WAITS_S), z odliczaniem w pasku statusu. Użytkownik może w tym czasie kliknąć „Zatrzymaj”."""
        rounds = step.get("_osm_rounds", 0)
        if rounds >= len(OVERPASS_RETRY_WAITS_S):
            return False
        wait = OVERPASS_RETRY_WAITS_S[rounds]
        step["_osm_rounds"] = rounds + 1
        step["_osm_tried"] = []
        step.setdefault("_param_overrides", {})["SERVER"] = svc.OVERPASS_SERVERS[0]
        self.log.emit("warning", tr("Wszystkie serwery Overpass są przeciążone – ponowię automatycznie za %d s "
                                    "(runda %d z %d). „Zatrzymaj” przerywa oczekiwanie.") % (
            wait, rounds + 1, len(OVERPASS_RETRY_WAITS_S)))
        rid = self._run_id
        self._start_countdown(wait, tr("Serwery OpenStreetMap przeciążone – ponowienie za %d s…"),
                              lambda: self._run_current(rid))
        return True

    def _start_countdown(self, seconds, text_fmt, done):
        self._stop_countdown()
        rid = self._run_id
        state = {"left": int(seconds)}
        timer = QTimer(self)
        timer.setInterval(1000)

        def tick():
            if rid != self._run_id or not self.running:
                timer.stop()
                return
            state["left"] -= 1
            if state["left"] > 0:
                self.statusText.emit(text_fmt % state["left"])
                return
            timer.stop()
            self._countdown = None
            self.statusText.emit(tr("Wykonuję plan…"))
            done()

        timer.timeout.connect(tick)
        self.statusText.emit(text_fmt % state["left"])
        timer.start()
        self._countdown = timer

    def _stop_countdown(self):
        if self._countdown is not None:
            self._countdown.stop()
            self._countdown.deleteLater()
            self._countdown = None

    # ---------------------------------------------------------------- kontrola wyniku
    def _input_layers(self, params):
        """[(warstwa, liczba obiektów)] dla wektorowych warstw wejściowych algorytmu."""
        out = []
        for key, v in params.items():
            for item in (v if isinstance(v, list) else [v]):
                selected = False
                if isinstance(item, QgsProcessingFeatureSourceDefinition):
                    selected = item.selectedFeaturesOnly
                    src = item.source
                    item = src.staticValue() if hasattr(src, "staticValue") else str(src)
                if isinstance(item, QgsVectorLayer):
                    lyr = item
                elif isinstance(item, str) and item and key.upper() not in ("EXPRESSION", "FORMULA", "FILTER"):
                    lyr = QgsProject.instance().mapLayer(item)
                    if lyr is None:
                        found = QgsProject.instance().mapLayersByName(item)
                        lyr = found[0] if found else None
                else:
                    lyr = None
                if isinstance(lyr, QgsVectorLayer) and lyr.isValid() and all(lyr is not x for x, _ in out):
                    try:
                        lyr.updateExtents()
                        count = lyr.selectedFeatureCount() if selected else int(lyr.featureCount())
                    except Exception:  # noqa: BLE001
                        count = -1
                    out.append((lyr, count))
        return out

    def _check_empty_result(self, inputs, produced):
        """Pusty wynik z niepustych danych wejściowych to zwykle błąd (warstwy się nie nakładają, zły układ
        współrzędnych, zły warunek) – plan ma się wtedy zatrzymać, a nie ogłaszać sukces."""
        prj = QgsProject.instance()
        empty = []
        for lid in produced.values():
            lyr = prj.mapLayer(lid) if isinstance(lid, str) else None
            if isinstance(lyr, QgsVectorLayer) and all(lyr is not x for x, _ in inputs):
                try:
                    if lyr.featureCount() == 0:
                        empty.append(lyr)
                except Exception:  # noqa: BLE001
                    pass
        filled = [(lyr, n) for lyr, n in inputs if n and n > 0]
        if not empty or not filled:
            return None
        desc = ", ".join("„%s” (%s)" % (lyr.name(), _n_features(n)) for lyr, n in filled)
        msg = tr("Wynik „%s” jest pusty, choć warstwy wejściowe mają obiekty: %s.") % (empty[0].name(), desc)
        exts = []
        for lyr, _ in filled:
            ext = _extent_in_project(lyr)
            if ext is None:
                msg += " " + tr("Warstwa „%s” nie ma zasięgu.") % lyr.name() + _native_extent_hint(lyr)
            else:
                exts.append(ext)
        made_by_plan = {v for res in self.results.values() for v in res.values() if isinstance(v, str)}
        if len(exts) >= 2 and not _extents_overlap(exts):
            msg += " " + tr("Zasięgi warstw wejściowych w ogóle się nie pokrywają – leżą w innych miejscach mapy "
                            "(inny obszar albo błędny układ współrzędnych).")
            for lyr, _ in filled:
                msg += _native_extent_hint(lyr)
        elif any(lyr.id() not in made_by_plan for lyr, _ in filled):
            msg += " " + tr("Jeśli istniejąca warstwa projektu jest niepełna albo dotyczy innego obszaru, zamiast ją "
                            "przekształcać pobierz nowe dane (np. z OpenStreetMap albo usług GUGiK). Sprawdź też "
                            "warunek wyboru.")
        else:
            msg += " " + tr("Sprawdź warunek wyboru albo to, czy obiekty rzeczywiście się nakładają.")
        return msg

    def _collect_outputs(self, step, alg, context, results):
        prj = QgsProject.instance()
        base = step.get("output_name") or step["title"]
        produced, texts, first_layer = {}, [], True
        for out in alg.outputDefinitions():
            name = out.name()
            if name not in results:
                continue
            val = results[name]
            is_layer_out = isinstance(out, _LAYER_OUTPUT_CLASSES) or isinstance(val, QgsMapLayer)
            if not is_layer_out:
                produced[name] = val if isinstance(val, (int, float, str, bool, type(None))) else str(val)
                if name not in ("OUTPUT_HTML_FILE",) and not isinstance(val, (list, dict)):
                    texts.append("%s = %s" % (name, str(val)[:80]))
                continue
            if isinstance(val, str) and prj.mapLayer(val):   # algorytm działał na istniejącej warstwie
                produced[name] = val
                continue
            layer = self._take_layer(val, context)
            if layer is None or not layer.isValid():
                produced[name] = val if isinstance(val, str) else str(val)
                continue
            layer.setName(base if first_layer else "%s (%s)" % (base, name))
            prj.addMapLayer(layer)
            produced[name] = layer.id()
            if first_layer:
                produced.setdefault("OUTPUT", layer.id())
                if isinstance(layer, QgsVectorLayer):
                    texts.append(tr("%s: %d obiektów") % (layer.name(), layer.featureCount()))
                else:
                    texts.append(tr("Dodano warstwę %s") % layer.name())
            first_layer = False
        return produced, texts

    @staticmethod
    def _take_layer(val, context):
        if isinstance(val, QgsMapLayer):
            return val
        if not isinstance(val, str) or not val:
            return None
        lyr = context.takeResultLayer(val)
        if lyr is not None:
            return lyr
        lyr = QgsProcessingUtils.mapLayerFromString(val, context, True)
        if lyr is not None:
            return lyr.clone() if QgsProject.instance().mapLayer(lyr.id()) is None else None
        vl = QgsVectorLayer(val, tr("wynik"), "ogr")
        if vl.isValid():
            return vl
        rl = QgsRasterLayer(val, "wynik")
        return rl if rl.isValid() else None

    # ---------------------------------------------------------------- okno algorytmu
    def _do_processing_dialog(self, step):
        import processing
        params = self._resolve(step.get("params") or {})
        before = set(QgsProject.instance().mapLayers().keys())
        results = processing.execAlgorithmDialog(step["algorithm"], params)
        new = [i for i in QgsProject.instance().mapLayers().keys() if i not in before]
        if not results and not new:  # okno zamknięte bez uruchomienia algorytmu
            step["_result_text"] = tr("Okno zamknięte bez uruchomienia – krok pominięty.")
            self._mark(step, SKIPPED)
            self.log.emit("warning", tr("Pominięto krok: %s") % step["title"])
            self._next()
            return
        res = {"OUTPUT": new[0]} if new else {}
        self._complete(step, res, tr("Nowe warstwy: %d") % len(new))

    # ---------------------------------------------------------------- wczytanie warstwy
    def _do_load_layer(self, step):
        provider = str(step.get("provider") or "").lower()
        uri = str(self._resolve(step.get("uri") or step.get("url") or ""))
        name = step.get("name") or step["title"]
        if not uri:
            raise StepError(tr("Brak adresu (uri) warstwy."))
        remote = svc.remote_source(uri) if provider in ("ogr", "gdal", "") else None
        if remote:
            # dane spod adresu http(s) – pobiera je wtyczka (jak serwer geoportalu); adres w sieci wewnętrznej
            # (np. ukryty w nazwie warstwy cudzego projektu) wymaga zgody użytkownika
            url, opts = remote
            self._require_consent(step, url, tr("adres w sieci wewnętrznej: %s") % url,
                                  lambda: self._download_data(step, svc.overpass_readable(url), opts, name))
            return
        needs_ok = provider in LOCAL_PROVIDERS or "/vsi" in uri.lower() or uri.lower().startswith("file:")
        if needs_ok and self.idx not in self._confirmed_loads:
            # plik lub baza wskazane przez model – tylko za zgodą użytkownika (audyt B2)
            self._mark(step, WAITING)
            self.confirmLoad.emit(self.idx, "%s: %s" % (provider, uri))
            return
        service_url = svc.uri_http_url(uri)
        if service_url:
            # usługi WMS/WMTS/XYZ/WFS/… – ten sam wymóg zgody dla adresów wewnętrznych co w „add_service”
            self._require_consent(step, service_url,
                                  tr("usługa %s w sieci wewnętrznej: %s") % (provider.upper(), service_url),
                                  lambda: self._load_provider_layer(step, provider, uri, name))
            return
        self._load_provider_layer(step, provider, uri, name)

    def _load_provider_layer(self, step, provider, uri, name):
        raster_providers = {"wms": "wms", "wmts": "wms", "xyz": "wms", "gdal": "gdal",
                            "wcs": "wcs", "arcgismapserver": "arcgismapserver"}
        vector_providers = {"wfs": "WFS", "oapif": "OAPIF", "ogr": "ogr", "arcgisfeatureserver": "arcgisfeatureserver",
                            "delimitedtext": "delimitedtext", "spatialite": "spatialite", "memory": "memory"}
        if provider in raster_providers:
            layer = QgsRasterLayer(uri, name, raster_providers[provider])
        elif provider in vector_providers:
            layer = QgsVectorLayer(uri, name, vector_providers[provider])
        else:
            raise StepError(tr("Nieobsługiwany dostawca danych „%s”.") % provider)
        if not layer.isValid():
            err = layer.error().summary() if layer.error() else ""
            raise StepError(tr("Nie udało się wczytać warstwy (%s). %s\n"
                            "Możesz wczytać ją ręcznie i pominąć ten krok albo poprosić AI o poprawkę.")
                            % (provider, err))
        QgsProject.instance().addMapLayer(layer)
        self._complete(step, {"OUTPUT": layer.id()}, tr("Wczytano: %s") % layer.name())

    def confirm_load(self, accepted):
        step = self.current()
        if not step or step["_status"] != WAITING or step["action"] not in ("load_layer", "add_service"):
            return
        if not accepted:
            self._mark(step, SKIPPED)
            self.log.emit("warning", tr("Pominięto krok: %s") % step["title"])
            self._next()
            return
        self._confirmed_loads.add(self.idx)
        self._run_current(self._run_id)

    # ---------------------------------------------------------------- adresy w sieci wewnętrznej
    def _abort_lookup(self):
        if self._dns_lookup is not None:
            try:
                QHostInfo.abortHostLookup(self._dns_lookup)
            except Exception:  # noqa: BLE001
                pass
            self._dns_lookup = None

    def _require_consent(self, step, url, label, proceed):
        """Wykonuje proceed(), gdy adres jest publiczny albo użytkownik już zatwierdził ten krok; w przeciwnym razie
        wstrzymuje plan (confirmLoad). Nazwy hostów rozwiązuje asynchronicznie (QHostInfo), więc interfejs QGIS
        nie zamarza przy wolnym DNS lub braku sieci."""
        if self.idx in self._confirmed_loads:
            proceed()
            return
        verdict = svc.private_url_static(url)
        if verdict is not None:
            self._after_consent_check(step, verdict, label, proceed)
            return
        host = urlsplit(str(url)).hostname or ""
        rid = self._run_id

        def resolved(info):
            if rid != self._run_id or not self.running or step is not self.current():
                return
            self._dns_lookup = None
            ips = []
            for addr in info.addresses():
                try:
                    ips.append(ipaddress.ip_address(addr.toString().split("%")[0]))
                except ValueError:
                    continue
            private = info.error() != QHostInfo.HostInfoError.NoError or not ips or svc.ips_private(ips)
            self._after_consent_check(step, private, label, proceed)

        self.log.emit("debug", tr("Sprawdzam adres: %s") % host)
        self._dns_lookup = QHostInfo.lookupHost(host, resolved)

    def _after_consent_check(self, step, private, label, proceed):
        if private:
            self._mark(step, WAITING)
            self.confirmLoad.emit(self.idx, label)
            return
        try:   # proceed() może wykonać się z wywołania zwrotnego DNS – poza blokiem try w _run_current
            proceed()
        except StepError as e:
            self._fail(step, str(e))
        except Exception as e:  # noqa: BLE001
            QgsMessageLog.logMessage(traceback.format_exc(), LOG_TAG, Qgis.MessageLevel.Critical)
            self._fail(step, "%s: %s" % (type(e).__name__, e))

    # ---------------------------------------------------------------- pobieranie (usługi, dane spod adresu)
    def _fetch(self, url, limit_bytes, callback, dest=None, timeout_s=DOWNLOAD_TIMEOUT_S):
        """GET przez menedżera sieci QGIS (proxy, certyfikaty).

        callback(błąd, status, dane|ścieżka, typ MIME, początek danych, rozmiar).

        Limit rozmiaru przerywa pobieranie, a odpowiedź z przerwanego uruchomienia planu jest ignorowana."""
        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b"User-Agent", b"QGIS-GIS-Assistant-AI")
        try:
            req.setTransferTimeout(int(timeout_s) * 1000)
        except AttributeError:
            pass
        try:
            req.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                             QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        except AttributeError:
            pass
        reply = QgsNetworkAccessManager.instance().get(req)
        _extend_qgis_timeout(reply, int(timeout_s) * 1000)
        self._net_reply = reply
        rid = self._run_id
        st = {"size": 0, "head": b"", "buf": bytearray(), "over": False, "redirect_blocked": None,
              "fh": open(dest, "wb") if dest else None}  # noqa: SIM115 – zamykany w finished()
        origin_private = svc.private_url_static(url)

        def redirected(target):
            # przekierowanie do komputera lokalnego / sieci wewnętrznej przerywamy od razu, zanim pójdzie żądanie
            # (nazwy hostów wymagałyby DNS – te sprawdzamy po adresie końcowym, bez blokowania interfejsu)
            t = target.toString()
            if svc.private_url_static(t) is True and origin_private is not True:
                st["redirect_blocked"] = t
                reply.abort()

        def ready():
            if rid != self._run_id or st["over"]:
                return
            chunk = bytes(reply.readAll())
            st["size"] += len(chunk)
            if len(st["head"]) < 4096:
                st["head"] += chunk[:4096 - len(st["head"])]
            if st["size"] > limit_bytes:
                st["over"] = True
                reply.abort()
                return
            if st["fh"] is not None:
                st["fh"].write(chunk)
            else:
                st["buf"].extend(chunk)

        def finished():
            try:
                if rid == self._run_id and not st["over"]:
                    ready()
            finally:
                if st["fh"] is not None:
                    st["fh"].close()
                reply.deleteLater()
            if rid != self._run_id or not self.running:
                _remove(dest)   # pobieranie przerwane („Zatrzymaj”) – nie zostawiamy pliku .part
                return
            if self._net_reply is reply:
                self._net_reply = None
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            status = int(status) if status else None
            ctype = str(reply.header(QNetworkRequest.KnownHeaders.ContentTypeHeader) or "")
            err = None
            final = reply.url().toString()
            if st["redirect_blocked"]:
                err = tr("Przekierowanie do sieci wewnętrznej zostało zablokowane.")
            elif st["over"]:
                err = tr("Dane są większe niż %d MB – ogranicz obszar albo zakres zapytania.") % (
                    limit_bytes // 1048576)
            elif status and status >= 400:
                err = tr("Serwer zwrócił błąd %d.") % status
            elif reply.error() != QNetworkReply.NetworkError.NoError:
                err = reply.errorString()
                if reply.error() == QNetworkReply.NetworkError.OperationCanceledError:
                    err = tr("Serwer nie odpowiedział w wyznaczonym czasie – ogranicz obszar zapytania.")
            elif final and final != url and svc.private_url_static(final) is True and origin_private is not True:
                err = tr("Przekierowanie do sieci wewnętrznej zostało zablokowane.")
            data = dest if dest else bytes(st["buf"])
            callback(err, status, data, ctype, st["head"], st["size"])

        def on_progress(received, total):
            if rid != self._run_id or not self.running or dest is None:
                return
            if total > 0:
                self.progress.emit(min(100.0, received * 100.0 / total))
                self.statusText.emit(tr("Pobieram: %s z %s") % (_mb(received), _mb(total)))
            else:
                self.statusText.emit(tr("Pobieram: %s") % _mb(received))

        reply.readyRead.connect(ready)
        reply.downloadProgress.connect(on_progress)
        reply.finished.connect(finished)
        try:
            reply.redirected.connect(redirected)
        except AttributeError:  # pragma: no cover – bardzo stare Qt
            pass

    # ---------------------------------------------------------------- usługa sieciowa (add_service)
    def _do_add_service(self, step):
        kind = str(step.get("service_type") or "wms").lower()
        url = str(self._resolve(step.get("url") or "")).strip()
        if kind not in svc.TYPES:
            raise StepError(tr("Nieznany typ usługi „%s” (dozwolone: WMS, WMTS, WFS, WCS).") % kind)
        try:
            caps = svc.capabilities_url(kind, url)
        except svc.ServiceError as e:
            raise StepError(str(e)) from None
        self._require_consent(step, url, tr("usługa %s w sieci wewnętrznej: %s") % (kind.upper(), url),
                              lambda: self._fetch_capabilities(step, kind, url, caps))

    def _fetch_capabilities(self, step, kind, url, caps):
        self.log.emit("debug", "GetCapabilities: %s" % svc.redact_url(caps))
        self._fetch(caps, MAX_CAPS_MB * 1048576,
                    lambda err, status, data, ctype, head, size, s=step, k=kind, u=url:
                    self._service_ready(s, k, u, err, data), timeout_s=90)

    def _service_ready(self, step, kind, url, err, data):
        try:
            if err:
                raise StepError(tr("Usługa pod adresem %s nie odpowiada poprawnie jako %s: %s")
                                % (url, kind.upper(), err))
            try:
                info = svc.parse_capabilities(kind, data, url)
            except svc.ServiceError as e:
                raise StepError(tr("Usługa pod adresem %s nie odpowiada poprawnie jako %s: %s")
                                % (url, kind.upper(), e)) from None
            wanted = step.get("layers") or []
            picked = svc.match_layers(info["layers"], wanted)
            if not picked:
                raise StepError(tr("Usługa „%s” działa, ale nie ma warstwy pasującej do „%s”. Dostępne warstwy: %s.")
                                % (info.get("title") or url, ", ".join(map(str, wanted)) or "-",
                                   svc.layers_sample(info["layers"])))
            layers = [self._service_layer(kind, info, ly) for ly in picked]
        except StepError as e:
            self._fail(step, str(e))
            return
        except Exception as e:  # noqa: BLE001
            QgsMessageLog.logMessage(traceback.format_exc(), LOG_TAG, Qgis.MessageLevel.Critical)
            self._fail(step, "%s: %s" % (type(e).__name__, e))
            return
        prj = QgsProject.instance()
        outputs = {}
        for i, lyr in enumerate(layers):
            prj.addMapLayer(lyr)
            outputs["OUTPUT" if i == 0 else "OUTPUT_%d" % (i + 1)] = lyr.id()
        if kind in ("wms", "wmts"):
            self._show_service_extent([ly.get("bbox") for ly in picked])
        names = ", ".join("„%s”" % lyr.name() for lyr in layers)
        self._complete(step, outputs, tr("Dodano z usługi %s „%s”: %s") % (
            kind.upper(), info.get("title") or url, names))

    def _service_layer(self, kind, info, ly):
        """Warstwa QGIS dla warstwy usługi (układ: najpierw układ projektu, potem EPSG:2180, 3857, 4326)."""
        prj_crs = QgsProject.instance().crs().authid() if QgsProject.instance().crs().isValid() else ""
        title = (ly.get("title") or ly["name"])[:120]
        uri = QgsDataSourceUri()
        if kind == "wms":
            crs = svc.pick_crs(ly.get("crs"), [prj_crs])
            if not crs:
                raise StepError(tr("Warstwa „%s” usługi nie podaje obsługiwanego układu współrzędnych.") % title)
            for k, v in (("contextualWMSLegend", "0"), ("crs", crs), ("dpiMode", "7"),
                         ("format", svc.pick_format(info.get("formats"))), ("layers", ly["name"]), ("styles", ""),
                         ("url", info["url"])):
                uri.setParam(k, v)
            layer = QgsRasterLayer(bytes(uri.encodedUri()).decode("utf-8"), title, "wms")
        elif kind == "wmts":
            ms = svc.pick_matrix_set(ly.get("matrix_sets"), [prj_crs])
            if not ms:
                raise StepError(tr("Warstwa „%s” nie ma siatki kafli (TileMatrixSet).") % title)
            for k, v in (("contextualWMSLegend", "0"), ("crs", svc.epsg(ms.get("crs")) or "EPSG:3857"),
                         ("dpiMode", "7"), ("format", svc.pick_format(ly.get("formats"))), ("layers", ly["name"]),
                         ("styles", ly.get("style") or "default"), ("tileMatrixSet", ms["id"]),
                         ("url", svc.capabilities_url("wmts", info["url"]))):
                uri.setParam(k, v)
            layer = QgsRasterLayer(bytes(uri.encodedUri()).decode("utf-8"), title, "wms")
        elif kind == "wfs":
            crs = svc.pick_crs(ly.get("crs"), [prj_crs]) or "EPSG:2180"
            for k, v in (("url", info["url"]), ("typename", ly["name"]), ("version", "auto"), ("srsname", crs),
                         ("pagingEnabled", "true")):
                uri.setParam(k, v)
            layer = QgsVectorLayer(uri.uri(False), title, "WFS")
        else:
            uri.setParam("url", info["url"])
            uri.setParam("identifier", ly["name"])
            layer = QgsRasterLayer(bytes(uri.encodedUri()).decode("utf-8"), title, "wcs")
        if not layer.isValid():
            err = layer.error().summary() if layer.error() else ""
            raise StepError(tr("QGIS nie wczytał warstwy „%s” z usługi %s. %s") % (title, kind.upper(), err))
        return layer

    def _show_service_extent(self, bboxes):
        """Usługi obrazowe: gdy bieżący widok nie obejmuje usługi, mapa przybliża się do jej zasięgu (WGS84)."""
        boxes = [b for b in bboxes if b and len(b) == 4 and all(math.isfinite(float(v)) for v in b)]
        if not boxes:
            return
        try:
            canvas = self.iface.mapCanvas()
            dest = canvas.mapSettings().destinationCrs()
            xf = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), dest, QgsProject.instance())
            ext = xf.transformBoundingBox(QgsRectangle(*[float(v) for v in boxes[0]]))
            for b in boxes[1:]:
                ext.combineExtentWith(xf.transformBoundingBox(QgsRectangle(*[float(v) for v in b])))
            if ext.isEmpty() or canvas.extent().intersects(ext):
                return
            canvas.setExtent(ext)
            canvas.refresh()
            self.log.emit("info", tr("Przybliżono mapę do zasięgu usługi."))
        except Exception:  # noqa: BLE001 – brak przybliżenia nie jest błędem kroku
            pass

    # ---------------------------------------------------------------- dane spod adresu (load_layer z http)
    def _download_data(self, step, url, opts, name, mirrors=None):
        if mirrors is None:
            mirrors = svc.overpass_mirror_urls(url)
        dest = os.path.join(QgsProcessingUtils.tempFolder(), "gis_assistant_%s.part" % uuid.uuid4().hex[:10])
        self.log.emit("info", tr("Pobieram dane: %s") % url[:160])
        self._fetch(url, MAX_DOWNLOAD_MB * 1048576,
                    lambda err, status, path, ctype, head, size, s=step, u=url, o=opts, n=name, m=mirrors:
                    self._data_ready(s, u, o, n, m, err, status, path, ctype, head, size), dest=dest)

    def _data_ready(self, step, url, opts, name, mirrors, err, status, path, ctype, head, size):
        try:
            if err:
                busy = svc.busy_status(status) or "czasie" in err or "time" in err.lower()
                if busy and mirrors:
                    self.log.emit("warning", tr("Serwer Overpass jest przeciążony – próbuję serwera zapasowego."))
                    _remove(path)
                    self._download_data(step, mirrors[0], opts, name, mirrors[1:])
                    return
                if svc.is_overpass(url):
                    err += " " + tr("Ogranicz obszar zapytania (np. do gminy) albo spróbuj później.")
                raise StepError(tr("Nie udało się pobrać danych: %s") % err)
            if svc.overpass_error(head):
                raise StepError(tr("Overpass API przerwał zapytanie (zwykle limit czasu albo pamięci) – ogranicz "
                                   "obszar, np. do gminy."))
            ext = svc.sniff_ext(head, ctype, url)
            if not ext:
                raise StepError(tr("Nie rozpoznano formatu pobranych danych (to może być strona WWW z komunikatem "
                                   "błędu zamiast danych)."))
            final = path[:-len(".part")] + ext
            os.replace(path, final)
            layer = _open_downloaded(final, ext, opts, name)
        except StepError as e:
            _remove(path)
            self._fail(step, str(e))
            return
        except Exception as e:  # noqa: BLE001
            QgsMessageLog.logMessage(traceback.format_exc(), LOG_TAG, Qgis.MessageLevel.Critical)
            self._fail(step, "%s: %s" % (type(e).__name__, e))
            return
        QgsProject.instance().addMapLayer(layer)
        mb = "%.1f MB" % (size / 1048576) if size >= 104858 else "%d kB" % max(1, round(size / 1024))
        warning = None
        if isinstance(layer, QgsVectorLayer):
            count = layer.featureCount()
            text = tr("Pobrano „%s” (%s, %s)") % (layer.name(), _n_features(count), mb)
            if count == 0:
                warning = tr("Pobrane dane „%s” nie zawierają obiektów – zapytanie mogło objąć zły obszar "
                             "albo zły warunek.") % layer.name()
        else:
            text = tr("Pobrano „%s” (%s)") % (layer.name(), mb)
        self._complete(step, {"OUTPUT": layer.id()}, text, warning)

    # ---------------------------------------------------------------- BDOT10k (paczki powiatowe GUGiK)
    def _do_bdot10k_layer(self, step):
        """Pobiera paczkę BDOT10k powiatu z danych otwartych GUGiK (GPKG → SHP → GML) i wczytuje jedną klasę
        obiektów. Paczka jest pamiętana na czas sesji – kolejne klasy z tego samego powiatu nie pobierają jej
        ponownie."""
        cls = svc.bdot10k_class(step.get("class") or step.get("layer") or step.get("klasa")
                                or step.get("object_class"))
        if not cls:
            raise StepError(tr("Brak kodu klasy BDOT10k (np. OT_BUBD_A – budynki, OT_SKDR_L – drogi)."))
        powiat = self._bdot10k_powiat(step)
        name = str(step.get("name") or step.get("output_name") or "").strip() or cls
        cached = self._bdot_cache.get(powiat)
        if cached and os.path.exists(cached):
            self.log.emit("info", tr("Paczka BDOT10k powiatu %s jest już pobrana – wczytuję klasę %s.") % (powiat, cls))
            self._bdot10k_load(step, cached, powiat, cls, name)
            return
        self._bdot10k_fetch(step, powiat, cls, name, svc.bdot10k_package_urls(powiat))

    def _bdot10k_powiat(self, step):
        """TERYT powiatu z kroku; referencja „{{sN}}” do warstwy ULDK bierze kod z jej pola „teryt”."""
        raw = step.get("teryt") or step.get("powiat") or step.get("teryt_powiat") or ""
        if isinstance(raw, str) and "{{" in raw:
            lyr = self.get_layer(raw)
            if isinstance(lyr, QgsVectorLayer):
                idx = lyr.fields().lookupField("teryt")
                if idx >= 0:
                    raw = next((str(f[idx]) for f in lyr.getFeatures()), "")
        code = svc.bdot10k_powiat_code(raw)
        if not code:
            raise StepError(tr("Brak kodu TERYT powiatu dla paczki BDOT10k (np. „1418”; gmina „141805_2” też "
                               "wystarczy – paczki są powiatowe)."))
        return code

    def _bdot10k_fetch(self, step, powiat, cls, name, urls):
        url, rest = urls[0], urls[1:]
        dest = os.path.join(QgsProcessingUtils.tempFolder(), "gis_assistant_bdot10k_%s.part" % uuid.uuid4().hex[:8])
        self.log.emit("info", tr("Pobieram paczkę BDOT10k powiatu %s: %s") % (powiat, url))
        self._fetch(url, BDOT10K_MAX_MB * 1048576,
                    lambda err, status, path, ctype, head, size, s=step, p=powiat, c=cls, n=name, r=rest, u=url:
                    self._bdot10k_ready(s, p, c, n, r, u, err, status, path, head, size), dest=dest)

    def _bdot10k_ready(self, step, powiat, cls, name, rest, url, err, status, path, head, size):
        try:
            not_zip = not err and not (head or b"").startswith(b"PK")
            if (err and status in (403, 404) and rest) or (not_zip and rest):
                _remove(path)
                self.log.emit("debug", tr("Paczka pod adresem %s jest niedostępna – próbuję kolejny format.") % url)
                self._bdot10k_fetch(step, powiat, cls, name, rest)
                return
            if err:
                if status == 404:
                    err = tr("brak paczki dla tego powiatu (sprawdź kod TERYT: %s).") % powiat
                raise StepError(tr("Nie udało się pobrać paczki BDOT10k powiatu %s: %s") % (powiat, err))
            if not_zip:
                raise StepError(tr("Serwer GUGiK zwrócił coś innego niż archiwum ZIP (%s).") % url)
            final = path[:-len(".part")] + ".zip"
            os.replace(path, final)
        except StepError as e:
            _remove(path)
            self._fail(step, str(e))
            return
        self._bdot_cache[powiat] = final
        self.statusText.emit(tr("Wykonuję plan…"))
        self.log.emit("success", tr("Pobrano paczkę BDOT10k powiatu %s (%s).") % (powiat, _mb(size)))
        self._bdot10k_load(step, final, powiat, cls, name)

    def _bdot10k_load(self, step, zip_path, powiat, cls, name):
        try:
            layer = _bdot10k_layer(zip_path, cls, name)
        except StepError as e:
            self._fail(step, str(e))
            return
        except Exception as e:  # noqa: BLE001
            QgsMessageLog.logMessage(traceback.format_exc(), LOG_TAG, Qgis.MessageLevel.Critical)
            self._fail(step, "%s: %s" % (type(e).__name__, e))
            return
        QgsProject.instance().addMapLayer(layer)
        count = layer.featureCount()
        warning = None
        if count == 0:
            warning = tr("Klasa %s w paczce BDOT10k powiatu %s nie zawiera obiektów.") % (cls, powiat)
        self._complete(step, {"OUTPUT": layer.id()},
                       tr("Wczytano „%s” (%s) z BDOT10k powiatu %s") % (layer.name(), _n_features(count), powiat),
                       warning)

    # ---------------------------------------------------------------- ULDK GUGiK
    def _do_uldk_boundary(self, step):
        level = str(step.get("level") or "").lower().replace("ó", "o").replace("ę", "e").replace("ł", "l")
        level = {"województwo": "wojewodztwo", "wojewodztwa": "wojewodztwo", "obręb": "obreb",
                 "działka": "dzialka", "dzialki": "dzialka"}.get(level, level)
        if level not in ULDK_LEVELS:
            raise StepError(tr("Nieznany poziom jednostki ULDK: %s") % step.get("level"))
        teryt = step.get("teryt") or step.get("id_teryt") or step.get("code")
        codes = [str(t).strip() for t in (teryt if isinstance(teryt, list) else [teryt]) if str(t or "").strip()]
        if not codes:
            raise StepError(tr("Brak kodu TERYT jednostki."))
        name = step.get("name") or step["title"]
        vl = QgsVectorLayer("MultiPolygon?crs=EPSG:2180", name, "memory")
        pr = vl.dataProvider()
        pr.addAttributes([QgsField(n, _STRING_TYPE) for n in ("teryt", "nazwa", "powiat", "wojewodztwo")])
        vl.updateFields()
        self._uldk_layer = vl
        self._uldk_queue = list(codes)
        self._uldk_level = level
        self._uldk_step = step
        self._uldk_next()

    def _uldk_next(self):
        if not self._uldk_queue:
            vl, step = self._uldk_layer, self._uldk_step
            if vl.featureCount() == 0:
                self._fail(step, tr("ULDK nie zwróciło żadnej geometrii."))
                return
            vl.updateExtents()
            QgsProject.instance().addMapLayer(vl)
            self._complete(step, {"OUTPUT": vl.id()}, tr("%s: %d obiekt(y)") % (vl.name(), vl.featureCount()))
            return
        code = self._uldk_queue.pop(0)
        request, result = ULDK_LEVELS[self._uldk_level]
        url = ULDK_URL + "?" + urlencode({"request": request, "id": code, "result": result, "srid": "2180"})
        self.log.emit("debug", "ULDK: %s" % url)
        req = QNetworkRequest(QUrl(url))
        try:
            req.setTransferTimeout(60000)
        except AttributeError:
            pass
        reply = QgsNetworkAccessManager.instance().get(req)
        self._net_reply = reply
        rid = self._run_id
        reply.finished.connect(lambda r=reply, c=code, i=rid: self._uldk_reply(r, c, i))

    def _uldk_reply(self, reply, code, rid):
        try:
            if rid != self._run_id or not self.running:
                return  # odpowiedź z przerwanego uruchomienia
            if self._net_reply is reply:
                self._net_reply = None
            step = self._uldk_step
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self._fail(step, tr("Błąd połączenia z ULDK: %s") % reply.errorString())
                return
            text = bytes(reply.readAll()).decode("utf-8", "replace")
        finally:
            reply.deleteLater()
        feats = self._parse_uldk(text, code)
        if not feats:
            self._fail(step, tr("ULDK nie znalazło jednostki o kodzie „%s” (%s). Odpowiedź: %s")
                       % (code, self._uldk_level, text.strip()[:120]))
            return
        self._uldk_layer.dataProvider().addFeatures(feats)
        self._uldk_next()

    def _parse_uldk(self, text, code):
        """Odpowiedź ULDK: 1. linia = status, kolejne = "SRID=2180;WKT|teryt|nazwa|…|województwo"."""
        feats = []
        for line in text.splitlines():
            line = line.strip()
            if not line or ("|" not in line and "(" not in line):
                continue  # linia statusu, np. "0"
            low = line.lower()
            if low.startswith("-1") or "brak wynik" in low or "błęd" in low:
                continue
            parts = [p.strip() for p in line.split("|")]
            wkt = parts[0]
            if wkt.upper().startswith("SRID=") and ";" in wkt:
                wkt = wkt.split(";", 1)[1]
            geom = QgsGeometry.fromWkt(wkt)
            if geom is None or geom.isEmpty():
                continue
            geom.convertToMultiType()
            teryt = parts[1] if len(parts) > 1 and parts[1] else code
            nazwa = parts[2] if len(parts) > 2 else ""
            woj = parts[-1] if len(parts) > 2 else ""
            powiat = parts[-2] if self._uldk_level != "wojewodztwo" and len(parts) >= 4 else ""
            f = QgsFeature(self._uldk_layer.fields())
            f.setGeometry(geom)
            f.setAttributes([teryt, nazwa, powiat, woj])
            feats.append(f)
        return feats

    # ---------------------------------------------------------------- użytkownik
    def _do_user_action(self, step):
        self._mark(step, WAITING)
        self.waitingForUser.emit(self.idx)

    def _do_zoom(self, step):
        layer = self.get_layer(step.get("layer") or "")
        if layer is None:
            raise StepError(tr("Nie znaleziono warstwy do przybliżenia."))
        canvas = self.iface.mapCanvas()
        ext = layer.extent()
        if ext.isEmpty():
            self._complete(step, {}, tr("Warstwa jest pusta – brak zasięgu do przybliżenia."))
            return
        try:
            from qgis.core import QgsCoordinateTransform
            xform = QgsCoordinateTransform(layer.crs(), canvas.mapSettings().destinationCrs(), QgsProject.instance())
            ext = xform.transformBoundingBox(ext)
        except Exception:  # noqa: BLE001
            pass
        ext.scale(1.1)
        canvas.setExtent(ext)
        canvas.refresh()
        self.iface.setActiveLayer(layer)
        self._complete(step, {"OUTPUT": layer.id()})

    def _do_note(self, step):
        self._complete(step, {})

    # ---------------------------------------------------------------- python
    def _do_python(self, step):
        self._mark(step, WAITING)
        self.confirmPython.emit(self.idx)

    def run_python(self, accepted):
        step = self.current()
        if not step:
            return
        if not accepted:
            self._mark(step, SKIPPED)
            self.log.emit("warning", tr("Odrzucono wykonanie kodu Python – krok pominięty."))
            self._next()
            return
        self._mark(step, RUNNING)
        import processing
        from qgis import core as qcore
        ns = {name: getattr(qcore, name) for name in dir(qcore) if name.startswith("Qgs") or name == "Qgis"}
        ns.update({"iface": self.iface, "processing": processing, "QgsProject": QgsProject,
                   "results": {k: dict(v) for k, v in self.results.items()}, "get_layer": self.get_layer})
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                exec(compile(step.get("code") or "", "<gis_assistant_ai:%s>" % step["id"], "exec"), ns)  # noqa: S102
        except Exception:  # noqa: BLE001
            self._fail(step, traceback.format_exc(limit=3))
            return
        out = buf.getvalue().strip()
        if out:
            self.log.emit("info", out[:2000])
        res = ns.get("result") if isinstance(ns.get("result"), dict) else {}
        self._complete(step, res, out[:120] if out else None)


def _is_blank(value):
    return value is None or (isinstance(value, str) and value.strip().lower() in ("", "none", "null"))


def _fix_quickosm(params, log):
    """QuickOSM przyjmuje TYPE_MULTI_REQUEST wyłącznie jako „AND”/„OR” (po jednym na każdą dodatkową parę
    klucz=wartość). Model bywa niedokładny – normalizujemy, a przy jednym kluczu parametr usuwamy."""
    if "TYPE_MULTI_REQUEST" not in params:
        return
    keys = [k for k in str(params.get("KEY") or "").split(",") if k.strip()]
    raw = params.get("TYPE_MULTI_REQUEST")
    items = raw if isinstance(raw, (list, tuple)) else str(raw).replace(";", ",").split(",")
    mapping = {"and": "AND", "&": "AND", "&&": "AND", "i": "AND", "or": "OR", "|": "OR", "||": "OR", "lub": "OR"}
    ops = [mapping.get(str(i).strip().lower()) for i in items if str(i).strip()]
    if len(keys) <= 1 or not ops or None in ops:
        params.pop("TYPE_MULTI_REQUEST")
        if len(keys) > 1:  # niezrozumiały operator przy wielu kluczach – najczęstszy przypadek to „AND”
            params["TYPE_MULTI_REQUEST"] = ",".join(["AND"] * (len(keys) - 1))
        log.emit("debug", "QuickOSM: TYPE_MULTI_REQUEST %r -> %r" % (raw, params.get("TYPE_MULTI_REQUEST")))
        return
    ops = (ops + [ops[-1]] * len(keys))[:len(keys) - 1]
    params["TYPE_MULTI_REQUEST"] = ",".join(ops)


# Poprawki parametrów dla algorytmów konkretnych wtyczek (klucz = identyfikator dostawcy Processing).
_PARAM_FIXES = {"quickosm": _fix_quickosm}


def _clean_feedback(messages):
    """Komunikaty algorytmu bez śladu stosu Pythona (wtyczki często zgłaszają cały traceback)."""
    lines = []
    for msg in messages[-8:]:
        text = str(msg).strip()
        if "Traceback (most recent call last)" in text:
            tail = [ln.strip() for ln in text.splitlines() if ln.strip()]
            text = tail[-1] if tail else ""
        if text and text not in lines:
            lines.append(text)
    return "\n".join(lines[-4:])


def _unavailable_message(reg, alg_id):
    """Czytelny powód: brak wtyczki albo błędna nazwa – z listą algorytmów dostawcy (pomaga „Napraw z AI”)."""
    prov = alg_id.split(":", 1)[0].lower() if ":" in alg_id else ""
    ids = sorted(a.id() for a in reg.algorithms() if prov and a.id().lower().startswith(prov + ":"))
    if prov and not ids:
        return tr("Algorytm „%s” jest niedostępny – wtyczka dostarczająca algorytmy „%s” nie jest zainstalowana "
                  "lub włączona.") % (alg_id, prov)
    if ids:
        return tr("Algorytm „%s” jest niedostępny. Dostępne algorytmy dostawcy „%s”: %s.") % (
            alg_id, prov, ", ".join(ids[:25]))
    return tr("Algorytm „%s” jest niedostępny.") % alg_id


def _printable(params):
    out = {}
    for k, v in params.items():
        if isinstance(v, QgsProcessingFeatureSourceDefinition):
            out[k] = {"source": v.source.staticValue() if hasattr(v.source, "staticValue") else str(v.source),
                      "selected_only": v.selectedFeaturesOnly}
        else:
            out[k] = v if isinstance(v, (int, float, str, bool, list, dict, type(None))) else str(v)
    return out


# ------------------------------------------------------------------ pomocnicze (kontrola wyników, pliki)

def _is_quickosm(alg):
    try:
        return bool(alg.provider()) and alg.provider().id().lower() == "quickosm"
    except Exception:  # noqa: BLE001
        return False


def _reset_overpass(step):
    for key in ("_osm_tried", "_osm_server", "_osm_rounds", "_param_overrides"):
        step.pop(key, None)


def _n_features(n):
    """Liczba obiektów z polską odmianą (tłumaczenia mapują każdą formę na własną)."""
    if n is None or n < 0:
        return tr("liczba obiektów nieznana")
    if n == 1:
        return tr("%d obiekt") % n
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return tr("%d obiekty") % n
    return tr("%d obiektów") % n


def _layer_summary(lyr):
    """Opis warstwy wynikowej dla korekty planu: liczba obiektów, układ, zasięg (diagnoza pustych wyników)."""
    out = {"id": lyr.id(), "name": lyr.name(),
           "crs": lyr.crs().authid() if lyr.crs().isValid() else None}
    if isinstance(lyr, QgsVectorLayer):
        try:
            out["feature_count"] = int(lyr.featureCount())
        except Exception:  # noqa: BLE001
            pass
    try:
        e = lyr.extent()
        if not e.isNull() and not e.isEmpty():
            digits = 5 if lyr.crs().isValid() and lyr.crs().isGeographic() else 1
            out["extent"] = [round(v, digits) for v in (e.xMinimum(), e.yMinimum(), e.xMaximum(), e.yMaximum())]
    except Exception:  # noqa: BLE001
        pass
    return out


def _extent_in_project(lyr):
    try:
        lyr.updateExtents()
        e = lyr.extent()
        if e.isNull() or e.isEmpty() or not lyr.crs().isValid():
            return None
        vals = [e.xMinimum(), e.yMinimum(), e.xMaximum(), e.yMaximum()]
        if not all(math.isfinite(v) for v in vals):
            return None
        prj = QgsProject.instance()
        xf = QgsCoordinateTransform(lyr.crs(), prj.crs(), prj)
        t = xf.transformBoundingBox(e)
        return [t.xMinimum(), t.yMinimum(), t.xMaximum(), t.yMaximum()]
    except Exception:  # noqa: BLE001 – np. współrzędne poza zakresem układu
        return None


def _extents_overlap(exts):
    x0, y0 = max(e[0] for e in exts), max(e[1] for e in exts)
    x1, y1 = min(e[2] for e in exts), min(e[3] for e in exts)
    return x0 <= x1 and y0 <= y1


def _native_extent_hint(layer):
    """Zasięg w układzie warstwy i to, na jakie jednostki wyglądają liczby – do diagnozy błędnego układu."""
    if not isinstance(layer, QgsVectorLayer):
        return ""
    layer.updateExtents()
    e = layer.extent()
    if e.isEmpty() or e.isNull():
        return " " + tr("Obiekty nie mają poprawnych geometrii (puste albo nieskończone współrzędne) – dane mogły "
                        "zostać uszkodzone, np. przez przeliczenie ze złego układu; użyj warstwy źródłowej.")
    vals = [e.xMinimum(), e.yMinimum(), e.xMaximum(), e.yMaximum()]
    if not all(math.isfinite(v) for v in vals):
        return " " + tr("Współrzędne są nieskończone – dane zostały uszkodzone; użyj warstwy źródłowej.")
    deg = -180.5 <= vals[0] and vals[2] <= 180.5 and -90.5 <= vals[1] and vals[3] <= 90.5
    return " " + tr("Zasięg „%s” w układzie warstwy (%s): x %.6g…%.6g, y %.6g…%.6g – liczby wyglądają na %s.") % (
        layer.name(), layer.crs().authid() or tr("brak układu"), vals[0], vals[2], vals[1], vals[3],
        tr("stopnie (EPSG:4326)") if deg else tr("metry"))


def _guard_assign_crs(alg_id, params, get_layer):
    """Przypisanie układu (bez przeliczania) niepasującego do współrzędnych niszczy położenie obiektów:
    np. metry EPSG:2180 oznaczone jako stopnie WGS84 po przeliczeniu lądują poza kulą ziemską."""
    if alg_id not in ("native:assignprojection", "qgis:definecurrentprojection"):
        return
    layer = params.get("INPUT")
    if isinstance(layer, QgsProcessingFeatureSourceDefinition):
        src = layer.source
        layer = src.staticValue() if hasattr(src, "staticValue") else str(src)
    layer = layer if isinstance(layer, QgsMapLayer) else get_layer(str(layer)) if layer else None
    target = params.get("CRS")
    tcrs = target if isinstance(target, QgsCoordinateReferenceSystem) \
        else QgsCoordinateReferenceSystem(str(target or ""))
    if not isinstance(layer, QgsVectorLayer) or not tcrs.isValid():
        return
    layer.updateExtents()
    e = layer.extent()
    if e.isEmpty() or e.isNull():
        return
    deg = -180.5 <= e.xMinimum() and e.xMaximum() <= 180.5 and -90.5 <= e.yMinimum() and e.yMaximum() <= 90.5
    if tcrs.isGeographic() and not deg:
        raise StepError(tr("Nie przypisuję układu %s warstwie „%s”: jej współrzędne (np. %.0f, %.0f) są w metrach, "
                           "a ten układ jest w stopniach – obiekty trafiłyby poza kulę ziemską. Warstwa ma układ %s; "
                           "jeśli leży w złym miejscu, sprawdź dane źródłowe zamiast zmieniać układ.")
                        % (tcrs.authid(), layer.name(), e.xMinimum(), e.yMinimum(),
                           layer.crs().authid() or tr("nieznany")))
    if not tcrs.isGeographic() and deg and max(abs(e.xMaximum()), abs(e.yMaximum())) > 1:
        raise StepError(tr("Nie przypisuję układu %s warstwie „%s”: jej współrzędne (np. %.5f, %.5f) wyglądają na "
                           "stopnie geograficzne, a ten układ jest w metrach. Właściwy układ to najpewniej EPSG:4326.")
                        % (tcrs.authid(), layer.name(), e.xMinimum(), e.yMinimum()))


def _remove(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def _mb(n):
    n = float(n or 0)
    return "%.1f MB" % (n / 1048576) if n >= 104858 else "%d kB" % max(1, round(n / 1024))


def _bdot10k_layer(zip_path, cls, name):
    """Warstwa klasy BDOT10k z paczki powiatowej: plik nazwany kodem klasy (GPKG/SHP/GML-.xml) albo tabela
    w zbiorczym GeoPackage. Archiwum czytane bez rozpakowywania (/vsizip/)."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
    except zipfile.BadZipFile:
        raise StepError(tr("Pobrana paczka BDOT10k jest uszkodzona (ZIP).")) from None
    base = "/vsizip/" + zip_path.replace("\\", "/")
    named, gpkgs = svc.bdot10k_members(names, cls)
    for member in named:
        lyr = QgsVectorLayer("%s/%s" % (base, member), name, "ogr")
        if lyr.isValid():
            return lyr
    for member in gpkgs:
        uri = "%s/%s" % (base, member)
        sub = _sublayer_matching(uri, cls)
        if sub:
            lyr = QgsVectorLayer("%s|layername=%s" % (uri, sub), name, "ogr")
            if lyr.isValid():
                return lyr
    files = sorted({os.path.basename(n) for n in names if n.lower().endswith(svc.BDOT10K_DATA_EXTS)})
    shown = ", ".join(files[:10]) + ("…" if len(files) > 10 else "")
    raise StepError(tr("W paczce BDOT10k nie znaleziono klasy %s. Pliki w paczce: %s") % (cls, shown or "brak"))


def _sublayer_matching(uri, cls):
    """Nazwa podwarstwy (tabeli) zawierającej kod klasy; None, gdy brak albo QGIS nie potrafi jej wylistować."""
    try:
        details = QgsProviderRegistry.instance().querySublayers(uri)
    except Exception:  # noqa: BLE001 – starsze QGIS bez querySublayers albo nieczytelny plik
        return None
    cls_l = cls.lower()
    return next((d.name() for d in details if cls_l in d.name().lower()), None)


_DATA_EXTS = (".gpkg", ".geojson", ".json", ".shp", ".kml", ".gml", ".csv", ".tif", ".tiff")
_OSM_LAYERS = ("multipolygons", "lines", "points", "multilinestrings", "other_relations")


def _open_downloaded(path, ext, opts, name):
    """Warstwa z pobranego pliku; dane OSM są przepisywane do GeoPackage (liczba obiektów, zasięg, szybkie analizy)."""
    layername = opts.get("layername")
    if ext == ".osm":
        return _osm_to_gpkg(path, name, layername)
    if ext in (".tif", ".tiff"):
        layer = QgsRasterLayer(path, name, "gdal")
    elif ext == ".zip":
        layer = _open_zip(path, name, layername)
    elif ext == ".csv":
        layer = QgsVectorLayer(path + "|option:X_POSSIBLE_NAMES=lon*,lng,x,dlugosc*|option:Y_POSSIBLE_NAMES=lat*,y,"
                               "szerokosc*|option:KEEP_GEOM_COLUMNS=NO", name, "ogr")
        if layer.isValid() and not layer.crs().isValid():
            layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    else:
        layer = QgsVectorLayer(path + ("|layername=%s" % layername if layername else ""), name, "ogr")
    if layer is None or not layer.isValid():
        raise StepError(tr("Pobrane dane nie dają się otworzyć jako warstwa (%s).") % ext)
    return layer


def _open_zip(path, name, layername=None):
    layer = QgsVectorLayer("/vsizip/" + path + ("|layername=%s" % layername if layername else ""), name, "ogr")
    if layer.isValid():
        return layer
    try:
        with zipfile.ZipFile(path) as zf:
            members = [m for m in zf.namelist() if m.lower().endswith(_DATA_EXTS) and not m.startswith("__MACOSX")]
    except zipfile.BadZipFile:
        raise StepError(tr("Pobrany plik ZIP jest uszkodzony.")) from None
    for m in sorted(members, key=lambda x: _DATA_EXTS.index(os.path.splitext(x.lower())[1])):
        inner = "/vsizip/%s/%s" % (path, m)
        if m.lower().endswith((".tif", ".tiff")):
            lyr = QgsRasterLayer(inner, name, "gdal")
        else:
            lyr = QgsVectorLayer(inner + ("|layername=%s" % layername if layername else ""), name, "ogr")
        if lyr.isValid():
            return lyr
    raise StepError(tr("W pobranym archiwum ZIP nie ma danych przestrzennych, które QGIS potrafi otworzyć."))


def _writer_enum(enum, member):
    """Wartość wyliczenia QgsVectorFileWriter w nowej (zakresowej) albo starej konwencji API."""
    scoped = getattr(QgsVectorFileWriter, enum, None)
    return getattr(scoped, member) if scoped is not None and hasattr(scoped, member) \
        else getattr(QgsVectorFileWriter, member)


def _osm_to_gpkg(path, name, layername=None):
    order = [layername] if layername else list(_OSM_LAYERS)
    gpkg = path[:-len(".osm")] + ".gpkg"
    for lname in order:
        src = QgsVectorLayer("%s|layername=%s" % (path, lname), name, "ogr")
        if not src.isValid():
            continue
        opts = QgsVectorFileWriter.SaveVectorOptions()
        opts.driverName = "GPKG"
        opts.layerName = lname
        opts.actionOnExistingFile = _writer_enum(
            "ActionOnExistingFile", "CreateOrOverwriteLayer" if os.path.exists(gpkg) else "CreateOrOverwriteFile")
        res = QgsVectorFileWriter.writeAsVectorFormatV3(src, gpkg, QgsProject.instance().transformContext(), opts)
        if res[0] != _writer_enum("WriterError", "NoError"):
            continue
        out = QgsVectorLayer("%s|layername=%s" % (gpkg, lname), name, "ogr")
        if out.isValid() and (out.featureCount() > 0 or layername):
            return out
    raise StepError(tr("Pobrane dane OpenStreetMap nie zawierają obiektów do wczytania (sprawdź zapytanie Overpass: "
                       "[out:xml] i „out body;>;out skel qt;”)."))
