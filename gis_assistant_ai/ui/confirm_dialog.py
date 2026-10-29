# -*- coding: utf-8 -*-
"""Okno zatwierdzania działań o skutkach poza QGIS: kod PyQGIS, wczytanie lokalnego pliku."""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout

from ..constants import PLUGIN_NAME
from ..i18n import tr
from . import styles


class ConfirmDialog(QDialog):
    def __init__(self, parent, title, intro, content, warnings=(), accept_text=None):
        super().__init__(parent)
        pal = styles.palette_for(parent) if parent is not None else styles.LIGHT
        self.setWindowTitle(PLUGIN_NAME + " – " + title)
        self.setMinimumSize(560, 380)
        lay = QVBoxLayout(self)
        head = QLabel(intro)
        head.setWordWrap(True)
        lay.addWidget(head)
        if warnings:
            warn = QLabel("⚠ " + tr("Kod zawiera konstrukcje o skutkach poza projektem QGIS: %s. "
                                   "Zatwierdź tylko, jeśli rozumiesz, co robi.") % ", ".join(tr(w) for w in warnings))
            warn.setWordWrap(True)
            warn.setStyleSheet("color:%s;font-weight:600;" % pal["error"])
            lay.addWidget(warn)
        view = QPlainTextEdit(content)
        view.setReadOnly(True)
        view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        view.setFont(font)
        lay.addWidget(view, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        skip = QPushButton(tr("Pomiń"))
        skip.setDefault(True)          # domyślnie – bez wykonania
        skip.setAutoDefault(True)
        skip.clicked.connect(self.reject)
        run = QPushButton(accept_text or tr("Wykonaj"))
        run.setAutoDefault(False)
        run.clicked.connect(self.accept)
        buttons.addWidget(skip)
        buttons.addWidget(run)
        lay.addLayout(buttons)
        skip.setFocus(Qt.FocusReason.OtherFocusReason)
