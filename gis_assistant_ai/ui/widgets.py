# -*- coding: utf-8 -*-
"""Zwijana sekcja panelu: belka w kolorze sekcji + treść."""
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget

from ..i18n import tr
from . import icons


class CollapsibleSection(QFrame):
    toggled = pyqtSignal(bool)

    def __init__(self, title, variant, pal, parent=None):
        """variant: cmd | res | log – decyduje o kolorach nagłówka (styles.stylesheet)."""
        super().__init__(parent)
        self.pal = pal
        self.variant = variant
        self.setObjectName("section")
        self.setProperty("variant", variant)
        self._expanded = True

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.header = QFrame()
        self.header.setObjectName("sectionHeader")
        self.header.setProperty("variant", variant)
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.mousePressEvent = lambda _e: self.setExpanded(not self._expanded)
        h = QHBoxLayout(self.header)
        h.setContentsMargins(6, 5, 8, 5)
        h.setSpacing(6)

        self.chevron = QToolButton()
        self.chevron.setObjectName("chevron")
        self.chevron.setIconSize(icons.qsize(14))
        self.chevron.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chevron.setAutoRaise(True)
        self.chevron.clicked.connect(lambda: self.setExpanded(not self._expanded))
        h.addWidget(self.chevron)

        self.title = QLabel(title)
        self.title.setObjectName("sectionTitle")
        self.title.setProperty("variant", variant)
        h.addWidget(self.title)
        h.addStretch(1)
        self._header_layout = h

        self.body = QWidget()
        self.body.setObjectName("sectionBody")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(8, 8, 8, 8)
        self.body_layout.setSpacing(6)
        lay.addWidget(self.header)
        lay.addWidget(self.body, 1)
        self._update_chevron()

    # ------------------------------------------------------------------ API
    def add_header_widget(self, widget):
        self._header_layout.addWidget(widget)

    def isExpanded(self):  # noqa: N802
        return self._expanded

    def setExpanded(self, expanded):  # noqa: N802
        expanded = bool(expanded)
        if expanded == self._expanded:
            return
        self._expanded = expanded
        self.body.setVisible(expanded)
        self._update_chevron()
        self.toggled.emit(expanded)

    def _update_chevron(self):
        name = "chevron_down" if self._expanded else "chevron_right"
        self.chevron.setIcon(icons.icon(name, self.pal["title_" + self.variant], 14))
        self.chevron.setToolTip(tr("Zwiń sekcję") if self._expanded else tr("Rozwiń sekcję"))
        self.header.setProperty("collapsed", not self._expanded)
        self.header.style().unpolish(self.header)
        self.header.style().polish(self.header)


class ElidedLabel(QLabel):
    """Etykieta, która w wąskim panelu skraca tekst wielokropkiem zamiast wymuszać większą szerokość."""

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full = text
        self.setToolTip(text)
        from qgis.PyQt.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)
        self._update()

    def sizeHint(self):  # noqa: N802
        hint = super().sizeHint()
        hint.setWidth(self.fontMetrics().horizontalAdvance(self._full) + 4)
        return hint

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._update()

    def _update(self):
        shown = self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, max(0, self.width() - 2))
        if shown != self.text():
            super().setText(shown)
