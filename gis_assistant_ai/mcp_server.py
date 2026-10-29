# -*- coding: utf-8 -*-
"""Serwer MCP wewnątrz QGIS: lokalne gniazdo TCP (tylko 127.0.0.1) + mapowanie narzędzi na PlanExecutor.

Wszystko działa w wątku GUI (pętla zdarzeń Qt), więc wywołania API QGIS nie wymagają synchronizacji. Odpowiedź
HTTP na tools/call jest wysyłana dopiero, gdy krok w QGIS się zakończy – połączenie czeka (QTcpSocket nie blokuje
interfejsu). Wywołania narzędzi są wykonywane po jednym naraz.
"""
import json
import os
import secrets
import sys
import traceback

from qgis.core import Qgis, QgsApplication, QgsMessageLog, QgsProject, QgsSingleSymbolRenderer, QgsVectorLayer
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QObject, QTimer, pyqtSignal
from qgis.PyQt.QtNetwork import QHostAddress, QTcpServer

from . import mcp_protocol as proto
from .constants import LOG_TAG
from .context_builder import build_context, layer_info
from .executor import PlanExecutor
from .i18n import qgis_language, tr
from .plan_model import normalize, validate
from .utils import short_json

MCP_TOOL_TIMEOUT_S = 20 * 60        # najdłuższe kroki: pobranie paczki BDOT10k, duże algorytmy
MCP_DEFAULT_PORT = 8765

INSTRUCTIONS = {
    "pl": (
        "Sterujesz uruchomionym programem QGIS przez wtyczkę GIS Assistant AI. Zacznij od qgis_context. Warstwy "
        "wskazuj identyfikatorem (pole „id”). Odległości są w jednostkach układu warstwy. Źródła danych dla Polski: "
        "ULDK (granice jednostek i działek, uldk_boundary), BDOT10k (bdot10k_layer), OpenStreetMap przez Overpass "
        "API (load_layer z providerem ogr i adresem zapytania), usługi WMS/WFS (add_service – nie zgaduj adresów). "
        "Gdy nie znasz parametrów algorytmu, użyj algorithm_help. Pola warstwy sprawdzaj przez layer_info, "
        "zanim zbudujesz wyrażenie. Odpowiadaj użytkownikowi po polsku."
    ),
    "en": (
        "You control a running QGIS through the GIS Assistant AI plugin. Start with qgis_context. Refer to layers "
        "by id (the “id” field). Distances are in the layer CRS units. Data sources for Poland: ULDK "
        "(administrative and parcel boundaries, uldk_boundary), BDOT10k topographic database (bdot10k_layer), "
        "OpenStreetMap via the Overpass API (load_layer with provider ogr and a query URL), WMS/WFS services "
        "(add_service – never guess addresses). When you do not know an algorithm’s parameters, use "
        "algorithm_help. Check layer fields with layer_info before building expressions. Reply to the user in "
        "the language of the QGIS interface (%s)."
    ),
}


def instructions():
    lang = proto.normalize_lang(qgis_language())
    text = INSTRUCTIONS[lang]
    return text % qgis_language() if lang == "en" else text


def _log(level, text):
    lvl = {"error": Qgis.MessageLevel.Critical, "warning": Qgis.MessageLevel.Warning}.get(level,
                                                                                         Qgis.MessageLevel.Info)
    QgsMessageLog.logMessage("MCP: %s" % text, LOG_TAG, lvl)


def plugin_version():
    try:
        meta = os.path.join(os.path.dirname(__file__), "metadata.txt")
        with open(meta, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("version="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return "?"


class _ToolRun(QObject):
    """Jedno wywołanie narzędzia wykonywane przez własny PlanExecutor; zbiera dziennik i odpowiada raz."""

    def __init__(self, iface, plan, allow_internal, respond, parent=None):
        super().__init__(parent)
        self.plan = plan
        self.allow_internal = allow_internal
        self._respond = respond
        self.logs = []
        self.warnings = []
        self.done = False
        self.executor = PlanExecutor(iface, self)
        ex = self.executor
        ex.log.connect(lambda level, text: self.logs.append("[%s] %s" % (level, text)))
        ex.finished.connect(self._finished)
        ex.stepFailed.connect(self._failed)
        ex.stepWarning.connect(self._warning)
        ex.confirmLoad.connect(self._confirm_load)
        ex.waitingForUser.connect(lambda i: self._reject(tr("Krok wymagający działania użytkownika nie jest "
                                                           "dostępny przez MCP.")))
        ex.confirmPython.connect(lambda i: self._reject(tr("Kod PyQGIS nie jest dostępny przez MCP.")))
        ex.replanRequested.connect(lambda i: ex.continue_plan())
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(lambda: self._reject(tr("Przekroczono limit czasu (%d min).")
                                                        % (MCP_TOOL_TIMEOUT_S // 60)))

    def start(self):
        self._timer.start(MCP_TOOL_TIMEOUT_S * 1000)
        self.executor.start(self.plan)

    # -- sygnały executora
    def _confirm_load(self, idx, label):
        if self.done:
            return
        if self.allow_internal:
            self.executor.confirm_load(True)
        else:
            self._reject(tr("Adres w sieci wewnętrznej wymaga zgody: %s. Powtórz z allow_internal_network=true, "
                            "jeśli użytkownik się zgadza.") % label)

    def _warning(self, idx, text):
        if self.done:
            return
        self.warnings.append(text)
        self.executor.continue_plan()

    def _failed(self, idx, message):
        if self.done:
            return
        step = self.executor.steps[idx] if 0 <= idx < len(self.executor.steps) else {}
        self._finish(proto.tool_text(tr("Krok „%s” zakończył się błędem: %s") % (step.get("title", idx + 1),
                                                                                  message) + self._log_tail(),
                                     is_error=True))

    def _finished(self, ok):
        if self.done:
            return
        if not ok:
            self._finish(proto.tool_text(tr("Wykonanie przerwane.") + self._log_tail(), is_error=True))
            return
        summary = self.executor.done_summary()
        lines = []
        for item, step in zip(summary, [s for s in self.executor.steps if s.get("_status") in ("done", "skipped")]):
            out = item.get("output_layer") or {}
            lyr = QgsProject.instance().mapLayer(out.get("id") or "") if out else None
            if lyr is not None and hasattr(lyr, "fields"):
                out["fields"] = [f.name() for f in lyr.fields()][:60]
            item["result"] = step.get("_result_text", "")
            line = "%s: %s" % (item.get("title", ""), item["result"] or item.get("status", ""))
            if out.get("id"):
                line += " (warstwa id: %s)" % out["id"]
            lines.append(line)
        text = "\n".join(lines) or tr("Wykonano.")
        if self.warnings:
            text += "\n" + tr("Ostrzeżenia:") + "\n- " + "\n- ".join(self.warnings)
        self._finish(proto.tool_text(text, structured={"steps": summary, "warnings": self.warnings}))

    def _reject(self, message):
        self._finish(proto.tool_text(message + self._log_tail(), is_error=True), abort=True)

    def _log_tail(self):
        tail = [line for line in self.logs if not line.startswith("[debug]")][-8:]
        return ("\n\n" + tr("Dziennik:") + "\n" + "\n".join(tail)) if tail else ""

    def _finish(self, result, abort=False):
        if self.done:
            return
        self.done = True            # od tej chwili sygnały executora (np. finished(False) po abort) są ignorowane
        self._timer.stop()
        if self.executor.running:
            if abort:
                self.executor.abort()   # przerywa trwające pobieranie / algorytm
            else:
                self.executor.running = False   # po błędzie executor czekałby na decyzję; dla MCP decyzja = koniec
        self._respond(result)
        self.deleteLater()


class McpServer(QObject):
    """Serwer HTTP/JSON-RPC na 127.0.0.1:port z tokenem; jedno narzędzie naraz."""
    stateChanged = pyqtSignal(bool, str)   # działa?, komunikat

    def __init__(self, iface, settings, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.settings = settings
        self._server = None
        self._buffers = {}
        self._active = None
        self._dispatcher = proto.Dispatcher(self._call_tool, plugin_version(), instructions(), qgis_language())

    # -- cykl życia
    @property
    def running(self):
        return self._server is not None and self._server.isListening()

    @property
    def port(self):
        return self._server.serverPort() if self.running else None

    def token(self):
        tok = self.settings.value("mcp/token", "", str)
        if not tok:
            tok = self.renew_token()
        return tok

    def renew_token(self):
        tok = secrets.token_urlsafe(24)
        self.settings.set_value("mcp/token", tok)
        return tok

    def url(self):
        return "http://127.0.0.1:%d/mcp" % (self.port or self.settings.value("mcp/port", MCP_DEFAULT_PORT, int))

    def apply_settings(self):
        """Uruchamia / zatrzymuje / restartuje serwer zgodnie z ustawieniami (mcp/enabled, mcp/port)."""
        enabled = self.settings.value("mcp/enabled", False, bool)
        port = self.settings.value("mcp/port", MCP_DEFAULT_PORT, int)
        if not enabled:
            self.stop()
            return
        if self.running and self.port == port:
            return
        self.stop()
        self.start(port)

    def start(self, port):
        self._server = QTcpServer(self)
        self._server.newConnection.connect(self._on_connection)
        if not self._server.listen(QHostAddress(QHostAddress.SpecialAddress.LocalHost), int(port)):
            msg = tr("Serwer MCP nie może nasłuchiwać na porcie %d: %s") % (port, self._server.errorString())
            _log("error", msg)
            self._server.deleteLater()
            self._server = None
            self.stateChanged.emit(False, msg)
            return False
        self.token()
        msg = tr("Serwer MCP nasłuchuje na %s") % self.url()
        _log("info", msg)
        self.stateChanged.emit(True, msg)
        return True

    def stop(self):
        if self._server is not None:
            self._server.close()
            self._server.deleteLater()
            self._server = None
            self.stateChanged.emit(False, tr("Serwer MCP zatrzymany."))
        if self._active is not None and not self._active.done:
            self._active._reject(tr("Serwer MCP zatrzymany."))
        self._active = None

    # -- transport
    def _on_connection(self):
        while self._server is not None and self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            self._buffers[sock] = bytearray()
            sock.readyRead.connect(lambda s=sock: self._on_ready(s))
            sock.disconnected.connect(lambda s=sock: self._drop(s))

    def _drop(self, sock):
        self._buffers.pop(sock, None)
        sock.deleteLater()

    def _on_ready(self, sock):
        buf = self._buffers.get(sock)
        if buf is None:
            return
        buf.extend(bytes(sock.readAll()))
        try:
            parsed = proto.parse_http_request(buf)
        except ValueError as e:
            self._send(sock, proto.http_response(400, {"error": str(e)}))
            return
        if parsed is None:
            return
        method, path, headers, body, _used = parsed
        self._buffers[sock] = bytearray()
        if path.split("?")[0] == "/health":
            self._send(sock, proto.http_response(200, {"ok": True, "name": proto.SERVER_NAME,
                                                       "qgis": Qgis.version(), "plugin": plugin_version()}))
            return
        if not proto.authorized(headers, self.token()):
            self._send(sock, proto.http_response(401, {"error": "unauthorized"}))
            return
        if path.split("?")[0] != "/mcp":
            self._send(sock, proto.http_response(404, {"error": "not found"}))
            return
        if method == "DELETE":
            self._send(sock, proto.http_response(200, {}))
            return
        if method != "POST":
            self._send(sock, proto.http_response(405, {"error": "use POST"}))
            return
        try:
            msg = json.loads(body.decode("utf-8"))
        except ValueError:
            self._send(sock, proto.http_response(400, proto.rpc_error(None, proto.PARSE_ERROR, "Parse error")))
            return
        if isinstance(msg, list):   # paczka żądań – obsługujemy tylko pojedyncze (most nigdy nie wysyła paczek)
            self._send(sock, proto.http_response(400, proto.rpc_error(None, proto.INVALID_REQUEST,
                                                                      "batch not supported")))
            return

        def respond(reply):
            if reply is None:
                self._send(sock, proto.http_response(202, b""))
            else:
                self._send(sock, proto.http_response(200, reply))

        try:
            self._dispatcher.handle(msg, respond)
        except Exception as e:  # noqa: BLE001
            _log("error", traceback.format_exc())
            respond(proto.rpc_error(msg.get("id") if isinstance(msg, dict) else None, proto.INTERNAL_ERROR, str(e)))

    @staticmethod
    def _send(sock, data):
        try:
            sock.write(data)
            sock.flush()
            sock.disconnectFromHost()
        except RuntimeError:
            pass   # gniazdo już zamknięte po stronie klienta

    # -- narzędzia
    def _call_tool(self, name, args, respond):
        _log("info", tr("Wywołanie narzędzia %s: %s") % (name, short_json(args, 400)))
        sync = {"qgis_context": self._tool_context, "layer_info": self._tool_layer_info,
                "list_algorithms": self._tool_list_algorithms, "algorithm_help": self._tool_algorithm_help,
                "set_layer_style": self._tool_set_layer_style}
        if name in sync:
            try:
                respond(sync[name](args))
            except Exception as e:  # noqa: BLE001
                _log("error", traceback.format_exc())
                respond(proto.tool_text("%s: %s" % (type(e).__name__, e), is_error=True))
            return
        if self._active is not None and not self._active.done:
            respond(proto.tool_text(tr("QGIS wykonuje jeszcze poprzednie polecenie – spróbuj ponownie za chwilę."),
                                    is_error=True))
            return
        if name == "run_plan":
            plan = proto.plan_from_args(args)
        else:
            step = proto.tool_to_step(name, args)
            plan = {"type": "plan", "title": name, "steps": [step]}
        try:
            plan = normalize(plan)
            forbidden = [s["action"] for s in plan["steps"] if s["action"] in proto.MCP_FORBIDDEN_ACTIONS]
            if forbidden:
                respond(proto.tool_text(tr("Akcje niedostępne przez MCP: %s") % ", ".join(sorted(set(forbidden))),
                                        is_error=True))
                return
            plan = validate(plan)   # poprawia identyfikatory algorytmów; wątpliwości trafiają do _warnings kroków
        except Exception as e:  # noqa: BLE001
            respond(proto.tool_text(tr("Nieprawidłowe wywołanie: %s") % e, is_error=True))
            return
        run = _ToolRun(self.iface, plan, bool(args.get("allow_internal_network")), respond, self)
        for st in plan["steps"]:
            run.warnings.extend(str(w) for w in st.get("_warnings") or [])
        self._active = run
        run.start()

    # -- narzędzia synchroniczne
    def _tool_context(self, args):
        ctx = build_context(self.iface, self.settings)
        if args.get("samples"):
            for info in ctx.get("layers", []):
                lyr = QgsProject.instance().mapLayer(info.get("id", ""))
                if lyr is not None:
                    info.update(layer_info(lyr, True, True))
        for key in ("web_search", "python_allowed", "ui_language"):
            ctx.pop(key, None)
        return proto.tool_text(json.dumps(ctx, ensure_ascii=False, indent=1), structured=ctx)

    def _tool_layer_info(self, args):
        lyr = _find_layer(args.get("layer"))
        if lyr is None:
            return proto.tool_text(tr("Nie znaleziono warstwy: %s") % args.get("layer"), is_error=True)
        info = layer_info(lyr, True, bool(args.get("samples", True)))
        return proto.tool_text(json.dumps(info, ensure_ascii=False, indent=1), structured=info)

    def _tool_list_algorithms(self, args):
        q = str(args.get("query") or "").strip().lower()
        reg = QgsApplication.processingRegistry()
        hits = []
        for alg in reg.algorithms():
            if q in alg.id().lower() or q in alg.displayName().lower():
                hits.append({"id": alg.id(), "name": alg.displayName(), "provider": alg.provider().name()})
            if len(hits) >= 50:
                break
        text = "\n".join("%s – %s (%s)" % (h["id"], h["name"], h["provider"]) for h in hits) or tr("Brak wyników.")
        return proto.tool_text(text, structured={"algorithms": hits})

    def _tool_algorithm_help(self, args):
        alg = QgsApplication.processingRegistry().algorithmById(str(args.get("algorithm") or ""))
        if alg is None:
            return proto.tool_text(tr("Nie ma algorytmu: %s") % args.get("algorithm"), is_error=True)
        params = []
        for p in alg.parameterDefinitions():
            item = {"name": p.name(), "type": p.type(), "description": p.description(),
                    "optional": bool(p.flags() & _optional_flag()), "default": _jsonable(p.defaultValue())}
            if hasattr(p, "options"):
                try:
                    item["options"] = {i: o for i, o in enumerate(p.options())}
                except Exception:  # noqa: BLE001
                    pass
            params.append(item)
        outputs = [{"name": o.name(), "type": o.type()} for o in alg.outputDefinitions()]
        info = {"id": alg.id(), "name": alg.displayName(), "short_help": alg.shortHelpString()[:1500],
                "parameters": params, "outputs": outputs}
        return proto.tool_text(json.dumps(info, ensure_ascii=False, indent=1), structured=info)

    def _tool_set_layer_style(self, args):
        lyr = _find_layer(args.get("layer"))
        if lyr is None:
            return proto.tool_text(tr("Nie znaleziono warstwy: %s") % args.get("layer"), is_error=True)
        changes, skipped = [], []
        opacity = args.get("opacity")
        if opacity is None and args.get("transparency") is not None:
            opacity = 100 - float(args["transparency"])
        if opacity is not None:
            lyr.setOpacity(max(0.0, min(1.0, float(opacity) / 100.0)))
            changes.append(tr("krycie %d%%") % round(float(opacity)))
        symbol = None
        if isinstance(lyr, QgsVectorLayer):
            renderer = lyr.renderer()
            if isinstance(renderer, QgsSingleSymbolRenderer):
                symbol = renderer.symbol()
        for key in ("fill_color", "stroke_color", "stroke_width", "size"):
            if args.get(key) is None:
                continue
            if symbol is None:
                skipped.append(key)
                continue
            if key == "fill_color":
                color = QColor(str(args[key]))
                if not color.isValid():
                    return proto.tool_text(tr("Nieprawidłowy kolor: %s") % args[key], is_error=True)
                symbol.setColor(color)
                changes.append(tr("kolor %s") % color.name())
            elif key == "stroke_color":
                color = QColor(str(args[key]))
                if not color.isValid():
                    return proto.tool_text(tr("Nieprawidłowy kolor: %s") % args[key], is_error=True)
                if symbol.type() == _symbol_type("Line"):
                    symbol.setColor(color)
                else:
                    for i in range(symbol.symbolLayerCount()):
                        sl = symbol.symbolLayer(i)
                        if hasattr(sl, "setStrokeColor"):
                            sl.setStrokeColor(color)
                changes.append(tr("obrys %s") % color.name())
            elif key == "stroke_width":
                width = float(args[key])
                if symbol.type() == _symbol_type("Line"):
                    symbol.setWidth(width)
                else:
                    for i in range(symbol.symbolLayerCount()):
                        sl = symbol.symbolLayer(i)
                        if hasattr(sl, "setStrokeWidth"):
                            sl.setStrokeWidth(width)
                changes.append(tr("szerokość obrysu %.2f mm") % width)
            elif key == "size" and symbol.type() == _symbol_type("Marker"):
                symbol.setSize(float(args[key]))
                changes.append(tr("rozmiar %.2f mm") % float(args[key]))
            else:
                skipped.append(key)
        root = QgsProject.instance().layerTreeRoot()
        node = root.findLayer(lyr.id())
        if node is not None and args.get("visible") is not None:
            node.setItemVisibilityChecked(bool(args["visible"]))
            changes.append(tr("widoczna") if args["visible"] else tr("ukryta"))
        if node is not None and args.get("position") in ("top", "bottom"):
            parent = node.parent()
            clone = node.clone()
            if args["position"] == "top":
                parent.insertChildNode(0, clone)
            else:
                parent.addChildNode(clone)
            parent.removeChildNode(node)
            changes.append(tr("na wierzchu") if args["position"] == "top" else tr("na spodzie"))
        lyr.triggerRepaint()
        try:
            self.iface.layerTreeView().refreshLayerSymbology(lyr.id())
        except Exception:  # noqa: BLE001
            pass
        text = tr("Warstwa „%s”: %s") % (lyr.name(), ", ".join(changes) or tr("bez zmian"))
        if skipped:
            text += "\n" + tr("Pominięto (symbolizacja inna niż pojedynczy symbol albo niepasujący typ "
                              "geometrii): %s") % ", ".join(skipped)
        return proto.tool_text(text, structured={"layer_id": lyr.id(), "changed": changes, "skipped": skipped})


_instance = None


def instance():
    """Serwer utworzony przez wtyczkę (plugin.initGui); None poza QGIS."""
    return _instance


def set_instance(server):
    global _instance
    _instance = server


def _symbol_type(name):
    """Qgis.SymbolType.Marker/Line/Fill (QGIS ≥ 3.30) albo QgsSymbol.Marker/Line/Fill (starsze)."""
    try:
        return getattr(Qgis.SymbolType, name)
    except AttributeError:
        from qgis.core import QgsSymbol
        return getattr(QgsSymbol, name)


def _find_layer(ref):
    prj = QgsProject.instance()
    ref = str(ref or "")
    lyr = prj.mapLayer(ref)
    if lyr is None:
        found = prj.mapLayersByName(ref)
        lyr = found[0] if found else None
    return lyr


def _optional_flag():
    try:
        return Qgis.ProcessingParameterFlag.Optional
    except AttributeError:
        from qgis.core import QgsProcessingParameterDefinition
        return QgsProcessingParameterDefinition.FlagOptional


def _jsonable(v):
    try:
        json.dumps(v)
        return v
    except (TypeError, ValueError):
        return str(v) if v is not None else None


def bridge_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_bridge.py")


def python_for_bridge():
    """Interpreter do uruchamiania mostu przez Claude Desktop (most nie potrzebuje QGIS – tylko biblioteki
    standardowej). Kolejność: Python z katalogu apps\\Python3NN instalacji QGIS (pełna biblioteka obok pliku
    .exe, działa bez środowiska OSGeo4W), potem bieżący interpreter; na Windows wersja bez konsoli (pythonw)."""
    exe = sys.executable or "python3"
    w = "w" if os.name == "nt" else ""
    candidates = []
    if os.name == "nt":
        # instalacja QGIS: <root>\bin\qgis-bin.exe lub <root>\bin\python.exe → <root>\apps\Python3NN
        root = os.path.dirname(os.path.dirname(exe))
        for d in (os.path.join(root, "apps", "Python3%d" % sys.version_info.minor),
                  os.path.join(root, "apps", "Python3%d%d" % (sys.version_info.major, sys.version_info.minor)),
                  os.path.join(sys.prefix or "", ""), os.path.dirname(sys.executable or "")):
            if d:
                candidates += [os.path.join(d, "python%s.exe" % w), os.path.join(d, "python.exe")]
        # bin\pythonw.exe z OSGeo4W to launcher wymagający zmiennych środowiskowych – tylko jako ostatnia deska ratunku
        candidates += [os.path.join(os.path.dirname(exe), "python%s.exe" % w)]
    else:
        candidates += [exe, "python3"]
    for c in candidates:
        if c and os.path.exists(c) and not os.path.basename(c).lower().startswith("qgis"):
            return c
    return "python3" if os.name != "nt" else "python"


def config_snippet(server):
    return json.dumps(proto.claude_desktop_config(python_for_bridge(), bridge_path(), server.url(),
                                                  server.token(), lang=qgis_language()), ensure_ascii=False, indent=2)

