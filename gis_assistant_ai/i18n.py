# -*- coding: utf-8 -*-
"""Tłumaczenia wtyczki.

Język wynika z ustawień QGIS (Ustawienia › Opcje › Ogólne › Język) – bez odpytywania sieci.
Teksty źródłowe są po polsku; dla innych języków ładowany jest plik i18n/gis_assistant_ai_<język>.qm,
a gdy go brak – wersja angielska.
"""
import os

try:
    from qgis.core import QgsApplication, QgsSettings
    from qgis.PyQt.QtCore import QCoreApplication, QLocale, QTranslator
except ImportError:  # testy jednostkowe bez QGIS (utils, plan_model)
    QgsApplication = QgsSettings = QCoreApplication = QLocale = QTranslator = None

CONTEXT = "GISAssistantAI"
SOURCE_LANGUAGE = "pl"
FALLBACK_LANGUAGE = "en"
I18N_DIR = os.path.join(os.path.dirname(__file__), "i18n")

LANGUAGE_NAMES = {
    "pl": "polski", "en": "English", "de": "Deutsch", "uk": "українська", "cs": "čeština",
    "sk": "slovenčina", "fr": "français", "es": "español", "it": "italiano", "lt": "lietuvių",
}

_translator = None
_active = SOURCE_LANGUAGE


def tr(text):
    """Tłumaczy tekst interfejsu (kontekst wspólny dla całej wtyczki)."""
    if QCoreApplication is None:
        return text
    return QCoreApplication.translate(CONTEXT, text)


def N_(text):  # noqa: N802
    """Oznacza tekst do tłumaczenia bez tłumaczenia go w chwili importu (stałe modułów)."""
    return text


def qgis_locale():
    """Kod języka interfejsu QGIS, np. „pl_PL” albo „en_US”."""
    try:
        loc = QgsApplication.locale()
        if loc:
            return loc
    except Exception:  # noqa: BLE001
        pass
    s = QgsSettings()
    if s.value("locale/overrideFlag", False, bool):
        return s.value("locale/userLocale", "") or QLocale.system().name()
    return QLocale.system().name()


def qgis_language():
    return (qgis_locale() or SOURCE_LANGUAGE).split("_")[0].split("-")[0].lower()


def active_language():
    """Język, w którym faktycznie wyświetlany jest interfejs wtyczki."""
    return _active


def language_label(code=None):
    """Język dla modelu AI – ten sam co interfejs QGIS (nawet bez tłumaczenia wtyczki)."""
    code = code or qgis_language()
    name = LANGUAGE_NAMES.get(code)
    return "%s (%s)" % (name, code) if name else code


def install():
    """Wczytuje tłumaczenie zgodne z językiem QGIS. Wywoływane przy starcie wtyczki."""
    global _translator, _active
    uninstall()
    lang = qgis_language()
    if lang == SOURCE_LANGUAGE:
        _active = SOURCE_LANGUAGE
        return _active
    for candidate in (qgis_locale(), lang, FALLBACK_LANGUAGE):
        path = os.path.join(I18N_DIR, "gis_assistant_ai_%s.qm" % candidate)
        if os.path.exists(path):
            translator = QTranslator()
            if translator.load(path):
                QCoreApplication.installTranslator(translator)
                _translator = translator
                _active = candidate.split("_")[0]
                return _active
    _active = SOURCE_LANGUAGE
    return _active


def uninstall():
    global _translator, _active
    if _translator is not None:
        QCoreApplication.removeTranslator(_translator)
        _translator = None
    _active = SOURCE_LANGUAGE
