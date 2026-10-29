# -*- coding: utf-8 -*-
"""Testy w działającym QGIS (bez okna): moduły, kontekst, executor, panel."""
import importlib
import pkgutil

import pytest

pytest.importorskip("qgis.core")

from qgis.core import (  # noqa: E402
    QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer)
from qgis.gui import QgsMapCanvas, QgsMessageBar  # noqa: E402
from qgis.PyQt.QtCore import QEventLoop, QTimer  # noqa: E402
from qgis.PyQt.QtWidgets import QMainWindow, QToolBar  # noqa: E402

import gis_assistant_ai  # noqa: E402


class FakeIface:
    """Najmniejszy zestaw metod QgisInterface używanych przez wtyczkę."""

    def __init__(self):
        self.window = QMainWindow()
        self.canvas = QgsMapCanvas(self.window)
        self.bar = QgsMessageBar(self.window)
        self.active = None
        self.menu_actions = []
        self.docks = []

    def mainWindow(self):  # noqa: N802
        return self.window

    def mapCanvas(self):  # noqa: N802
        return self.canvas

    def messageBar(self):  # noqa: N802
        return self.bar

    def activeLayer(self):  # noqa: N802
        return self.active

    def setActiveLayer(self, layer):  # noqa: N802
        self.active = layer

    def addToolBar(self, name):  # noqa: N802
        return self.window.addToolBar(name)

    def addPluginToMenu(self, menu, action):  # noqa: N802
        self.menu_actions.append(action)

    def removePluginMenu(self, menu, action):  # noqa: N802
        self.menu_actions.remove(action)

    def registerMainWindowAction(self, action, shortcut):  # noqa: N802
        return True

    def unregisterMainWindowAction(self, action):  # noqa: N802
        return True

    def addDockWidget(self, area, dock):  # noqa: N802
        self.docks.append(dock)

    def removeDockWidget(self, dock):  # noqa: N802
        self.docks.remove(dock)


@pytest.fixture
def iface(qgis_app):
    yield FakeIface()
    QgsProject.instance().clear()


def _points_layer(name="szkoly", n=3):
    layer = QgsVectorLayer("Point?crs=EPSG:2180&field=nazwa:string",
                           name, "memory")
    feats = []
    for i in range(n):
        f = QgsFeature(layer.fields())
        f.setGeometry(QgsGeometry.fromPointXY(
            QgsPointXY(640000 + 500 * i, 480000)))
        f["nazwa"] = "Szkoła %d" % i
        feats.append(f)
    layer.dataProvider().addFeatures(feats)
    layer.updateExtents()
    QgsProject.instance().addMapLayer(layer)
    return layer


def _wait(signal, timeout_ms=60000):
    """Czeka na sygnał w pętli zdarzeń; zwraca jego argumenty."""
    got = []
    loop = QEventLoop()
    signal.connect(lambda *a: (got.append(a), loop.quit()))
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    assert got, "sygnał nie przyszedł w %d ms" % timeout_ms
    return got[0]


def test_all_modules_import(qgis_app):
    names = [m.name for m in pkgutil.walk_packages(
        gis_assistant_ai.__path__, "gis_assistant_ai.")]
    assert "gis_assistant_ai.ui.dock" in names
    for name in names:
        importlib.import_module(name)


def test_context_describes_layers_without_paths(iface):
    from gis_assistant_ai.context_builder import build_context, context_json
    from gis_assistant_ai.settings import Settings
    layer = _points_layer()
    iface.active = layer
    ctx = build_context(iface, Settings())
    assert ctx["active_layer"] == "szkoly"
    assert list(ctx)[-1] == "layers"  # warstwy na końcu (ucinane jako pierwsze)
    info = ctx["layers"][0]
    assert info["name"] == "szkoly"
    assert "native" in ctx["processing_providers"]
    assert "Szkoła" not in context_json(ctx)  # bez wartości atrybutów


def test_executor_runs_buffer_plan(iface):
    from gis_assistant_ai import plan_model
    from gis_assistant_ai.executor import PlanExecutor
    layer = _points_layer()
    plan = plan_model.validate(plan_model.normalize({
        "type": "plan", "title": "Bufor", "steps": [
            {"id": "s1", "action": "processing", "title": "Bufor 100 m",
             "algorithm": "native:buffer",
             "params": {"INPUT": layer.id(), "DISTANCE": 100,
                        "OUTPUT": "TEMPORARY_OUTPUT"}},
            {"id": "s2", "action": "note", "title": "Koniec"}]}))
    ex = PlanExecutor(iface)
    ex.start(plan)
    (ok,) = _wait(ex.finished)
    assert ok, [s.get("_error") for s in ex.steps]
    out = QgsProject.instance().mapLayer(ex.results["s1"]["OUTPUT"])
    assert out.featureCount() == 3
    summary = ex.done_summary()
    layer_summary = summary[0]["output_layer"]
    assert layer_summary["feature_count"] == 3
    assert len(layer_summary["extent"]) == 4


def test_executor_stops_on_empty_result(iface):
    from gis_assistant_ai import plan_model
    from gis_assistant_ai.executor import PlanExecutor
    layer = _points_layer()
    plan = plan_model.validate(plan_model.normalize({
        "type": "plan", "title": "Filtr", "steps": [
            {"id": "s1", "action": "processing", "title": "Wybór",
             "algorithm": "native:extractbyexpression",
             "params": {"INPUT": layer.id(), "EXPRESSION": "1 = 0",
                        "OUTPUT": "TEMPORARY_OUTPUT"}}]}))
    ex = PlanExecutor(iface)
    ex.start(plan)
    idx, message = _wait(ex.stepWarning)
    assert idx == 0 and message
    ex.abort()


def test_dock_builds_and_cleans_up(iface):
    from gis_assistant_ai.ui.dock import GISAssistantAIDock
    dock = GISAssistantAIDock(iface, iface.window)
    assert not dock.exec_btn.isEnabled()
    dock._new_conversation()
    dock.cleanup()
    dock.deleteLater()


def test_plugin_init_and_unload(iface):
    plugin = gis_assistant_ai.classFactory(iface)
    plugin.initGui()
    assert plugin.action in iface.menu_actions
    plugin.toggle()
    assert len(iface.docks) == 1
    plugin.unload()
    assert not iface.menu_actions and not iface.docks
    assert iface.window.findChild(QToolBar, "EnviroSolutions") is None \
        or not iface.window.findChild(QToolBar, "EnviroSolutions").actions()
