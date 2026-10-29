# -*- coding: utf-8 -*-
"""Normalizacja i walidacja odpowiedzi modelu."""
import difflib

from .utils import extract_json, find_refs, public_fields
from .i18n import tr
from .services import TYPES as SERVICE_TYPES

VALID_TYPES = {"plan", "tool", "answer", "clarify", "plan_revision"}
ACTIONS = {"processing", "load_layer", "uldk_boundary", "user_action", "zoom",
           "processing_dialog", "python", "note", "add_service",
           "bdot10k_layer"}
ACTION_ALIASES = {
    "algorithm": "processing", "run_algorithm": "processing",
    "processing_run": "processing",
    "add_layer": "load_layer", "load": "load_layer", "wms": "load_layer",
    "wfs": "load_layer",
    "uldk": "uldk_boundary", "boundary": "uldk_boundary",
    "bdot10k": "bdot10k_layer", "bdot": "bdot10k_layer",
    "bdot10k_class": "bdot10k_layer", "load_bdot10k": "bdot10k_layer",
    "bdot10k_download": "bdot10k_layer",
    "user": "user_action", "manual": "user_action", "ask_user": "user_action",
    "zoom_to_layer": "zoom", "code": "python", "pyqgis": "python",
    "info": "note",
    "dialog": "processing_dialog", "open_dialog": "processing_dialog",
    # krok samodzielny z Asystenta AI geoportalu: usługa znaleziona przez
    # model (GetCapabilities + dobór warstwy)
    "add_wms": "add_service", "add_wfs": "add_service",
    "add_wmts": "add_service", "add_wcs": "add_service",
    "service": "add_service", "web_service": "add_service",
    "add_web_service": "add_service",
}
# Częste pomyłki modeli w identyfikatorach algorytmów
ALG_ALIASES = {
    "qgis:buffer": "native:buffer", "qgis:centroids": "native:centroids",
    "qgis:clip": "native:clip", "qgis:intersection": "native:intersection",
    "qgis:dissolve": "native:dissolve",
    "qgis:reprojectlayer": "native:reprojectlayer",
    "qgis:extractbyexpression": "native:extractbyexpression",
    "qgis:extractbyattribute": "native:extractbyattribute",
    "qgis:extractbylocation": "native:extractbylocation",
    "qgis:difference": "native:difference", "qgis:union": "native:union",
    "qgis:mergevectorlayers": "native:mergevectorlayers",
    "qgis:fieldcalculator": "native:fieldcalculator",
    "qgis:joinattributesbylocation": "native:joinattributesbylocation",
    "native:selectbyexpression": "qgis:selectbyexpression",
    "native:selectbyattribute": "qgis:selectbyattribute",
    "qgis:selectbylocation": "native:selectbylocation",
    "qgis:countpointsinpolygon": "native:countpointsinpolygon",
    "qgis:fixgeometries": "native:fixgeometries",
    "qgis:multiparttosingleparts": "native:multiparttosingleparts",
}


def parse_response(text):
    """Zwróć znormalizowaną odpowiedź modelu z jej tekstu (JSON).

    Zgłasza ValueError, gdy w tekście nie ma obiektu JSON.
    """
    obj = extract_json(text)
    return normalize(obj)


def normalize(obj):
    """Uzupełnij typ odpowiedzi i jej pola (w miejscu); zwróć obiekt.

    Nieznany typ jest odgadywany z zawartości (steps, tools, question),
    kroki planu przechodzą przez normalize_steps.
    """
    t = str(obj.get("type", "")).strip().lower()
    if t not in VALID_TYPES:
        if obj.get("steps"):
            t = "plan"
        elif obj.get("tools"):
            t = "tool"
        elif obj.get("question"):
            t = "clarify"
        else:
            t = "answer"
    obj["type"] = t
    obj.setdefault("title", "")
    if t in ("plan", "plan_revision"):
        obj["steps"] = normalize_steps(obj.get("steps") or [])
    if t == "tool":
        tools = obj.get("tools") or []
        if isinstance(tools, dict):
            tools = [tools]
        obj["tools"] = [x for x in tools if isinstance(x, dict)][:5]
    if t == "answer":
        obj["text"] = str(obj.get("text") or obj.get("summary") or "")
    return obj


def normalize_steps(steps, taken_ids=None):
    """Zwróć kroki planu w postaci oczekiwanej przez executor.

    Ujednolica nazwy akcji i pól, nadaje unikalne id (z pominięciem
    taken_ids), usuwa pola „_…” ustawione przez model, a wątpliwości
    zapisuje w „_warnings”.
    """
    taken = set(taken_ids or [])
    out = []
    for i, s in enumerate(steps, 1):
        if not isinstance(s, dict):
            continue
        # pola zaczynające się od „_” to stan wtyczki – model nie może ich
        # ustawić
        s = {k: v for k, v in s.items() if not str(k).startswith("_")}
        action = str(s.get("action") or ("processing" if s.get("algorithm")
                                         else "note")).strip().lower()
        action = ACTION_ALIASES.get(action, action)
        if action not in ACTIONS:
            s.setdefault("_warnings", []).append(
                tr("Nieznany typ kroku „%s” – potraktowano jako informację.")
                % action)
            action = "note"
        s["action"] = action
        sid = str(s.get("id") or "s%d" % i).strip()
        base, n = sid, 2
        while sid in taken:
            sid = "%s_%d" % (base, n)
            n += 1
        taken.add(sid)
        s["id"] = sid
        s["title"] = str(s.get("title") or s.get("description")
                         or tr("Krok %d") % i)
        s.setdefault("description", "")
        if action in ("processing", "processing_dialog"):
            s["algorithm"] = str(s.get("algorithm") or s.get("algorithm_id")
                                 or "").strip()
            if not isinstance(s.get("params"), dict):
                s["params"] = {}
        if action == "bdot10k_layer":
            s["class"] = str(s.get("class") or s.get("layer")
                             or s.get("klasa") or s.get("object_class")
                             or "").strip()
            t = (s.get("teryt") or s.get("powiat") or s.get("teryt_powiat")
                 or "")
            s["teryt"] = str(t[0] if isinstance(t, list) and t else t).strip()
            if not s["class"]:
                s.setdefault("_warnings", []).append(
                    tr("Brak kodu klasy BDOT10k (np. OT_BUBD_A)."))
        if action == "add_service":
            kind = str(s.get("service_type") or s.get("kind")
                       or s.get("service") or s.get("provider") or "wms")
            s["service_type"] = kind.strip().lower()
            s["url"] = str(s.get("url") or s.get("uri") or "").strip()
            layers = (s.get("layers") or s.get("layer") or s.get("layer_name")
                      or [])
            s["layers"] = [str(x) for x in (layers if isinstance(layers, list)
                                            else [layers])
                           if str(x).strip()]
            if s["service_type"] not in SERVICE_TYPES:
                s.setdefault("_warnings", []).append(
                    tr("Nieznany typ usługi „%s” (dozwolone: WMS, WMTS, WFS, "
                       "WCS).") % s["service_type"])
        s["_status"] = "pending"
        out.append(s)
    return out


def best_match(alg_id, candidates, cutoff=0.8, margin=0.03):
    """Zwróć najbliższy identyfikator, gdy wyraźnie wygrywa z kolejnym.

    Model czasem przekręca nazwę algorytmu wtyczki (np.
    quickosm:downloadosmdatabyarea zamiast
    quickosm:downloadosmdatainareaquery); w obrębie jednego dostawcy można
    dopasować luźniej. Zwraca None, gdy nic nie pasuje dość dobrze.
    """
    scored = sorted(((difflib.SequenceMatcher(None, alg_id.lower(),
                                              c.lower()).ratio(), c)
                     for c in candidates), reverse=True)
    if not scored or scored[0][0] < cutoff:
        return None
    if len(scored) > 1 and scored[0][0] - scored[1][0] < margin:
        return None
    return scored[0][1]


def validate(obj):
    """Sprawdź algorytmy w rejestrze Processing i referencje między krokami.

    Poprawia identyfikatory algorytmów (w miejscu), a wątpliwości zapisuje
    w „_warnings” kroków; zwraca obiekt.
    """
    from qgis.core import QgsApplication
    reg = QgsApplication.processingRegistry()
    cache = {}

    def all_ids():
        # lista całego rejestru tylko wtedy, gdy identyfikator trzeba
        # poprawiać (zwykle wszystkie są poprawne)
        if "ids" not in cache:
            cache["ids"] = [a.id() for a in reg.algorithms()]
        return cache["ids"]

    def fix_alg(alg_id):
        if not alg_id:
            return None, tr("Brak identyfikatora algorytmu.")
        if reg.algorithmById(alg_id):
            return alg_id, None

        def fixed(new_id):
            return new_id, (tr("Poprawiono identyfikator %s → %s.")
                            % (alg_id, new_id))

        alias = ALG_ALIASES.get(alg_id.lower())
        if alias and reg.algorithmById(alias):
            return fixed(alias)
        has_prov = ":" in alg_id
        prov, name = alg_id.split(":", 1) if has_prov else ("", alg_id)
        if has_prov:
            for other in ("native", "qgis", "gdal"):
                cand = "%s:%s" % (other, name)
                if other != prov and reg.algorithmById(cand):
                    return fixed(cand)
        close = difflib.get_close_matches(alg_id, all_ids(), n=1,
                                          cutoff=0.88)
        if close:
            return fixed(close[0])
        prov = prov.lower()
        same = [a for a in all_ids()
                if prov and a.lower().startswith(prov + ":")]
        best = best_match(alg_id, same)
        if best:
            return fixed(best)
        if prov and not same:
            return alg_id, tr("Algorytm „%s” pochodzi z wtyczki, która nie "
                              "jest zainstalowana lub włączona (dostawca "
                              "Processing „%s”).") % (alg_id, prov)
        return alg_id, tr("Algorytm „%s” nie jest dostępny w tej instalacji "
                          "QGIS.") % alg_id

    if obj.get("type") in ("plan", "plan_revision"):
        known = set()
        for s in obj["steps"]:
            if s["action"] in ("processing", "processing_dialog"):
                new_id, warn = fix_alg(s["algorithm"])
                if new_id:
                    s["algorithm"] = new_id
                if warn:
                    s.setdefault("_warnings", []).append(warn)
            missing = find_refs(public_fields(s)) - known
            if missing and obj.get("type") == "plan":
                s.setdefault("_warnings", []).append(
                    tr("Odwołanie do nieznanego kroku: %s.")
                    % ", ".join(sorted(missing)))
            known.add(s["id"])
    elif obj.get("type") == "tool":
        for t in obj["tools"]:
            aid = t.get("algorithm_id")
            if aid:
                new_id, warn = fix_alg(aid)
                t["algorithm_id"] = (new_id if new_id
                                     and reg.algorithmById(new_id) else "")
                if warn and not t["algorithm_id"]:
                    t["_warning"] = warn
    return obj


def executable(obj):
    """Sprawdź, czy odpowiedź to plan z krokiem do wykonania.

    Plan z samymi notatkami (note) nie jest wykonywalny.
    """
    return bool(obj) and obj.get("type") == "plan" and any(
        s["action"] != "note" for s in obj.get("steps", []))
