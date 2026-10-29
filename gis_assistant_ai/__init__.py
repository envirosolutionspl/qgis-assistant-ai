# -*- coding: utf-8 -*-
"""GIS Assistant AI – wtyczka QGIS (3.34+ / 4.x)."""


def classFactory(iface):  # noqa: N802 (nazwa wymagana przez QGIS)
    from .plugin import GISAssistantAIPlugin
    return GISAssistantAIPlugin(iface)
