# -*- coding: utf-8 -*-
"""Wspólne ustawienia testów: uruchom ``pytest`` w katalogu repozytorium.

Testy modułów niezależnych od QGIS działają wszędzie. Testy z plików
``test_qgis_*.py`` korzystają z fikstury ``qgis_app`` i są pomijane, gdy
Python nie widzi pakietu ``qgis`` (w CI uruchamiane w obrazach qgis/qgis).
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_APP = None


@pytest.fixture(scope="session")
def qgis_app():
    """Aplikacja QGIS bez okna, z Processing i osobnym plikiem ustawień.

    ``qgis.testing.start_app`` zamyka QGIS (``exitQgis``) przy wyjściu
    z Pythona – bez tego proces potrafi się wysypać już po testach.
    """
    global _APP
    pytest.importorskip("qgis.core")
    from qgis.PyQt.QtCore import QCoreApplication, QSettings
    from qgis.testing import start_app

    if _APP is None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        # ustawienia testów w katalogu tymczasowym, nie w profilu
        # użytkownika (profil QGIS – QGIS_CUSTOM_CONFIG_PATH w start_app)
        QCoreApplication.setOrganizationName("EnviroSolutionsTests")
        QCoreApplication.setApplicationName("gis_assistant_ai_tests")
        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat,
                          QSettings.Scope.UserScope, tempfile.mkdtemp())
        _APP = start_app()
        _init_processing()
    return _APP


def _init_processing():
    """Inicjuje Processing (ścieżka do wtyczek systemowych QGIS)."""
    try:
        from processing.core.Processing import Processing
    except ImportError:
        from qgis.core import QgsApplication
        sys.path.append(os.path.join(QgsApplication.pkgDataPath(),
                                     "python", "plugins"))
        from processing.core.Processing import Processing
    Processing.initialize()
