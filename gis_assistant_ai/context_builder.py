# -*- coding: utf-8 -*-
"""Opis bieżącego projektu QGIS przekazywany modelowi AI.

Zawiera tylko to, co potrzebne do zaplanowania pracy: nazwy i identyfikatory
warstw, typy geometrii, układy współrzędnych, pola atrybutów. Źródła warstw
są oczyszczane z haseł, loginów, tokenów i pełnych ścieżek dysków
(sanitize_source). Przykładowe wartości atrybutów są wysyłane tylko po
włączeniu tej opcji.
"""
import json
import math

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsMapLayer,
    QgsProcessingAlgorithm,
    QgsProcessingParameterDefinition,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsWkbTypes,
)

from .constants import (MAX_CONTEXT_CHARS, MAX_CONTEXT_FIELDS,
                        MAX_CONTEXT_LAYERS)
from .i18n import language_label, qgis_locale
from .llm_client import LLMClient
from .utils import sanitize_source

_REMOTE_PROVIDERS = {"wfs", "oapif", "arcgisfeatureserver", "wms", "wcs",
                     "arcgismapserver"}


def qgis_flag(owner, new_path, old_name):
    """Zwróć flagę w nowej (Qgis.*) albo starej konwencji API.

    Np. Qgis.ProcessingParameterFlag istnieje dopiero od QGIS 3.36 (wtyczka
    działa od 3.34) – wtedy flaga pochodzi z owner.old_name.
    """
    try:
        cur = Qgis
        for part in new_path.split("."):
            cur = getattr(cur, part)
        return cur
    except AttributeError:
        return getattr(owner, old_name)


# Flagi Processing ustalane raz (używa ich też executor.py)
PARAM_OPTIONAL = qgis_flag(QgsProcessingParameterDefinition,
                           "ProcessingParameterFlag.Optional", "FlagOptional")
PARAM_HIDDEN = qgis_flag(QgsProcessingParameterDefinition,
                         "ProcessingParameterFlag.Hidden", "FlagHidden")
ALG_NO_THREADING = qgis_flag(QgsProcessingAlgorithm,
                             "ProcessingAlgorithmFlag.NoThreading",
                             "FlagNoThreading")


def _string_types():
    """Zwróć typy pól tekstowych w Qt5 i Qt6.

    QVariant.String (Qt5) i QMetaType.Type.QString (QGIS ≥ 3.38, Qt6).
    W PyQt6 wyliczenia nie są liczbami, więc porównanie z 10 tam nie działa.
    """
    out = set()
    try:
        from qgis.PyQt.QtCore import QVariant
        out.add(QVariant.String)
    except (ImportError, AttributeError):  # PyQt6 nie ma QVariant.String
        pass
    try:
        from qgis.PyQt.QtCore import QMetaType
        out.add(QMetaType.Type.QString)
    except (ImportError, AttributeError):
        pass
    return out


_STRING_TYPES = _string_types()


def layer_info(layer, with_fields=True, with_samples=False):
    """Zwróć opis warstwy dla modelu (słownik gotowy do JSON).

    Zawiera id, nazwę, dostawcę, układ, oczyszczone źródło i zasięg, a dla
    warstw wektorowych także geometrię, liczbę obiektów i pola (opcjonalnie
    z przykładowymi wartościami).
    """
    crs = layer.crs()
    crs_valid = crs.isValid()
    provider = layer.providerType()
    valid = layer.isValid()
    info = {
        "id": layer.id(),
        "name": layer.name(),
        "provider": provider,
        "crs": crs.authid() if crs_valid else None,
        "source": sanitize_source(layer.source(), provider),
    }
    if crs_valid and crs.isGeographic():
        info["crs_units"] = "stopnie"
    if valid:
        ext = layer_extent(layer)
        if ext:
            info["extent"] = ext
    if not valid:
        info["valid"] = False  # np. brak połączenia z bazą – bez odpytywania
        if isinstance(layer, QgsVectorLayer):
            info["kind"] = "vector"
        else:
            info["kind"] = ("raster" if isinstance(layer, QgsRasterLayer)
                            else "inna")
        return info
    if isinstance(layer, QgsVectorLayer):
        info["kind"] = "vector"
        info["geometry"] = QgsWkbTypes.displayString(layer.wkbType())
        try:
            info["feature_count"] = int(layer.featureCount())
        except Exception:  # noqa: BLE001
            info["feature_count"] = -1
        selected = layer.selectedFeatureCount()
        if selected:
            info["selected"] = selected
        subset = layer.subsetString()
        if subset:
            info["filter"] = subset[:200]
        if with_fields:
            fields = layer.fields()
            info["fields"] = ["%s (%s)" % (f.name(), f.typeName())
                              for f in list(fields)[:MAX_CONTEXT_FIELDS]]
            if fields.count() > MAX_CONTEXT_FIELDS:
                info["fields_truncated"] = fields.count()
            if with_samples and provider.lower() not in _REMOTE_PROVIDERS:
                info["samples"] = _samples(layer)
    elif isinstance(layer, QgsRasterLayer):
        info["kind"] = "raster"
        try:
            info["bands"] = layer.bandCount()
            info["size_px"] = [layer.width(), layer.height()]
        except Exception:  # noqa: BLE001
            pass
    else:
        info["kind"] = (type(layer).__name__.replace("Qgs", "")
                        .replace("Layer", "").lower() or "inna")
    return info


def layer_extent(layer):
    """Zwróć zasięg [xmin, ymin, xmax, ymax] w układzie warstwy albo None.

    Służy do diagnozy pustych wyników (rozłączne zasięgi = inny obszar albo
    zły układ). None także dla zasięgu pustego lub nieskończonego.
    """
    try:
        e = layer.extent()
        if e.isNull() or e.isEmpty():
            return None
        vals = [e.xMinimum(), e.yMinimum(), e.xMaximum(), e.yMaximum()]
        if not all(math.isfinite(v) for v in vals):
            return None
        digits = (5 if layer.crs().isValid() and layer.crs().isGeographic()
                  else 1)
        return [round(v, digits) for v in vals]
    except Exception:  # noqa: BLE001
        return None


def _samples(layer, per_field=5, max_fields=15):
    out = {}
    try:
        if layer.featureCount() > 500000:
            return out
    except Exception:  # noqa: BLE001
        return out
    fields = layer.fields()
    for idx, f in enumerate(fields):
        if len(out) >= max_fields:
            break
        type_name = f.typeName().lower()
        is_text = (f.type() in _STRING_TYPES
                   or any(t in type_name for t in ("char", "string", "text")))
        if not is_text:
            continue
        try:
            vals = [str(v)[:40] for v in layer.uniqueValues(idx, per_field)
                    if v not in (None, "")]
        except Exception:  # noqa: BLE001
            continue
        if vals:
            out[f.name()] = vals
    return out


def build_context(iface, settings):
    """Zwróć opis projektu QGIS dla modelu (słownik gotowy do JSON).

    Obejmuje wersję i język QGIS, układ i widok mapy, warstwy, dostawców
    i algorytmy Processing wtyczek oraz aktywne wtyczki.
    """
    prj = QgsProject.instance()
    with_samples = settings.value("send_samples", False, bool)
    ctx = {
        "qgis_version": Qgis.version(),
        "ui_locale": qgis_locale(),
        "ui_language": language_label(),
        "python_allowed": settings.value("allow_python", False, bool),
        # czy model ma narzędzie web_search (adresy usług, kody TERYT) – bez
        # niego nie wolno zgadywać adresów
        "web_search": LLMClient.web_search_available({
            "provider": settings.provider, "endpoint": settings.endpoint(),
            "model": settings.model(), "web_search": settings.web_search()}),
        "project": {
            "crs": prj.crs().authid() if prj.crs().isValid() else None,
            "crs_geographic": bool(prj.crs().isValid()
                                   and prj.crs().isGeographic()),
        },
    }
    try:
        ext = iface.mapCanvas().extent()
        ctx["project"]["map_extent"] = [round(float(ext.xMinimum()), 2),
                                        round(float(ext.yMinimum()), 2),
                                        round(float(ext.xMaximum()), 2),
                                        round(float(ext.yMaximum()), 2)]
    except Exception:  # noqa: BLE001
        pass

    nodes = prj.layerTreeRoot().findLayers()
    layers = []
    for node in nodes[:MAX_CONTEXT_LAYERS]:
        lyr = node.layer()
        if lyr is None or not isinstance(lyr, QgsMapLayer):
            continue
        info = layer_info(lyr, with_fields=True, with_samples=with_samples)
        info["visible"] = bool(node.isVisible())
        layers.append(info)
    if len(nodes) > MAX_CONTEXT_LAYERS:
        ctx["layers_truncated"] = len(nodes)
    active = iface.activeLayer()
    ctx["active_layer"] = (active.name() if isinstance(active, QgsMapLayer)
                           else None)

    reg = QgsApplication.processingRegistry()
    ctx["processing_providers"] = sorted(p.id() for p in reg.providers()
                                         if p.isActive())
    plugin_algs = plugin_algorithms(reg)
    if plugin_algs:
        ctx["plugin_algorithms"] = plugin_algs
    try:
        from qgis.utils import active_plugins
        ctx["installed_plugins"] = sorted(active_plugins)[:150]
    except Exception:  # noqa: BLE001
        pass

    # warstwy celowo na końcu: context_json() ucina zbyt długi opis od końca –
    # tracimy dalsze warstwy, a nie wersję QGIS, układ projektu czy listę
    # algorytmów
    ctx["layers"] = layers
    # za duży projekt – skracamy opisy dalszych warstw (przy ≤ 10 warstwach
    # nie ma czego skracać, więc bez json.dumps)
    if (len(layers) > 10
            and len(json.dumps(ctx, ensure_ascii=False)) > MAX_CONTEXT_CHARS):
        for info in layers[10:]:
            info.pop("fields", None)
            info.pop("samples", None)
            info.pop("source", None)
    return ctx


# Dostawcy wbudowani w QGIS – ich algorytmy model zna; algorytmy wtyczek (np.
# QuickOSM) podajemy jawnie, żeby model nie zgadywał identyfikatorów.
_CORE_PROVIDERS = {"native", "qgis", "gdal", "3d", "pdal", "grass", "grass7",
                   "grassprovider", "saga", "otb", "model", "script",
                   "project", "mdal"}
_MAX_PLUGIN_ALGS = 120
_MAX_PLUGIN_ALGS_CHARS = 6000


def plugin_algorithms(reg):
    """Zwróć {id: "PARAMETRY -> WYJŚCIA"} algorytmów wtyczek Processing.

    Obejmuje aktywnych dostawców spoza rdzenia QGIS; „?” oznacza parametr
    opcjonalny. Lista jest ograniczona liczbą algorytmów i znaków.
    """
    out, size = {}, 0
    for prov in sorted(reg.providers(), key=lambda p: p.id()):
        if not prov.isActive() or prov.id().lower() in _CORE_PROVIDERS:
            continue
        for alg in sorted(prov.algorithms(), key=lambda a: a.id()):
            try:
                params = [d.name() + ("?" if _optional(d) else "")
                          for d in alg.parameterDefinitions()
                          if not _hidden(d) and not d.isDestination()]
                outs = [o.name() for o in alg.outputDefinitions()]
                desc = "%s -> %s" % (", ".join(params),
                                     ", ".join(outs) or "-")
            except Exception:  # noqa: BLE001
                desc = ""
            size += len(alg.id()) + len(desc) + 8
            if len(out) >= _MAX_PLUGIN_ALGS or size > _MAX_PLUGIN_ALGS_CHARS:
                return out
            out[alg.id()] = desc
    return out


def _has_flag(param, flag):
    try:
        return bool(param.flags() & flag)
    except TypeError:
        return False


def _optional(param):
    return _has_flag(param, PARAM_OPTIONAL)


def _hidden(param):
    return _has_flag(param, PARAM_HIDDEN)


def context_json(ctx):
    """Zwróć kontekst jako JSON do promptu, ucięty do limitu znaków."""
    return json.dumps(ctx, ensure_ascii=False,
                      indent=1)[:MAX_CONTEXT_CHARS + 4000]
