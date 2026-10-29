# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QToolBar

try:  # Qt6: QAction w QtGui, Qt5: w QtWidgets
    from qgis.PyQt.QtGui import QAction
except ImportError:  # pragma: no cover
    from qgis.PyQt.QtWidgets import QAction

from .constants import ENV_MENU_NAME, ICON_PATH, LOG_TAG, PLUGIN_NAME
from . import mcp_server
from .settings import Settings
from . import i18n
from .i18n import tr


def _debug_log():
    """Błąd nieblokujący – zapisujemy ślad w dzienniku QGIS zamiast go ukrywać."""
    import traceback
    from qgis.core import Qgis, QgsMessageLog
    QgsMessageLog.logMessage(traceback.format_exc(), LOG_TAG, Qgis.MessageLevel.Info)


class GISAssistantAIPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.toolbar = None
        self.dock = None
        self.mcp = None
        self.menu = "&%s" % ENV_MENU_NAME
        # język zgodny z ustawieniem QGIS (Ustawienia › Opcje › Ogólne › Język)
        i18n.install()

    def initGui(self):  # noqa: N802
        # Wspólny pasek narzędzi wtyczek EnviroSolutions
        self.toolbar = self.iface.mainWindow().findChild(QToolBar, ENV_MENU_NAME)
        if not self.toolbar:
            self.toolbar = self.iface.addToolBar(ENV_MENU_NAME)
            self.toolbar.setObjectName(ENV_MENU_NAME)

        self.action = QAction(QIcon(ICON_PATH), PLUGIN_NAME, self.iface.mainWindow())
        self.action.setObjectName("gisAssistantAIAction")
        self.action.setToolTip(PLUGIN_NAME + tr(" – opisz, co chcesz zrobić w QGIS"))
        self.action.setCheckable(True)
        self.action.triggered.connect(self.toggle)
        self.toolbar.addAction(self.action)
        self.iface.addPluginToMenu(self.menu, self.action)
        try:  # skrót klawiszowy konfigurowalny w Ustawienia > Skróty klawiszowe
            self.iface.registerMainWindowAction(self.action, "Ctrl+Alt+A")
        except Exception:  # noqa: BLE001
            _debug_log()
        # serwer MCP (Claude Desktop) – nasłuchuje tylko, gdy włączony w ustawieniach
        try:
            self.mcp = mcp_server.McpServer(self.iface, Settings(), self.iface.mainWindow())
            mcp_server.set_instance(self.mcp)
            self.mcp.apply_settings()
        except Exception:  # noqa: BLE001 – brak serwera MCP nie może blokować wtyczki
            _debug_log()

    def unload(self):
        if self.mcp is not None:
            self.mcp.stop()
            mcp_server.set_instance(None)
            self.mcp.deleteLater()
            self.mcp = None
        if self.dock is not None:
            self.dock.cleanup()
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
        if self.action is not None:
            try:
                self.iface.unregisterMainWindowAction(self.action)
            except Exception:  # noqa: BLE001
                _debug_log()
            self.iface.removePluginMenu(self.menu, self.action)
            if self.toolbar is not None:
                self.toolbar.removeAction(self.action)
                if not self.toolbar.actions():  # pasek usuwamy tylko, gdy nie używa go inna wtyczka ES
                    self.toolbar.deleteLater()
            self.action = None
        self.toolbar = None
        from .settings import SecretStore
        SecretStore.clear_session()
        i18n.uninstall()

    def toggle(self, checked=None):
        if self.dock is None:
            from .ui.dock import GISAssistantAIDock
            self.dock = GISAssistantAIDock(self.iface, self.iface.mainWindow())
            self.dock.visibilityChanged.connect(self.action.setChecked)
            self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
            self.dock.show()
            self.dock.raise_()
            return
        visible = self.dock.isVisible() if checked is None else bool(checked)
        if checked is None:
            visible = not visible
        self.dock.setVisible(visible)
        if visible:
            self.dock.raise_()
