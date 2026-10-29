# -*- coding: utf-8 -*-
"""Ikony rysowane z SVG w kolorach palety marki (bez plików graficznych)."""
from qgis.PyQt.QtCore import QByteArray, QSize, Qt
from qgis.PyQt.QtGui import QIcon, QPainter, QPixmap

try:
    from qgis.PyQt.QtSvg import QSvgRenderer
except ImportError:  # pragma: no cover
    QSvgRenderer = None

# Gwiazdka nawiązująca do logo wtyczki.
SPARKLE = ("<path d='M12 2c.6 5.4 4.6 9.4 10 10-5.4.6-9.4 4.6-10 10-.6-5.4-4.6-9.4-10-10 5.4-.6 9.4-4.6 10-10z'"
           " fill='{c}'/>")
PLUS = ("<path d='M12 5v14M5 12h14' stroke='{c}' stroke-width='2' stroke-linecap='round' fill='none'/>")
SLIDERS = ("<g stroke='{c}' stroke-width='1.8' stroke-linecap='round' fill='none'>"
           "<path d='M4 7h9M17 7h3M4 17h3M11 17h9'/><circle cx='15' cy='7' r='2'/><circle cx='9' cy='17' r='2'/></g>")
_STROKE = "stroke='{c}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' fill='none'"
CHEVRON_DOWN = "<path d='M7 10l5 5 5-5' " + _STROKE + "/>"
CHEVRON_RIGHT = "<path d='M10 7l5 5-5 5' " + _STROKE + "/>"

SHAPES = {"sparkle": SPARKLE, "plus": PLUS, "sliders": SLIDERS,
          "chevron_down": CHEVRON_DOWN, "chevron_right": CHEVRON_RIGHT}


def svg(name, color):
    return ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>%s</svg>"
            % SHAPES[name].format(c=color)).encode("utf-8")


def pixmap(name, color, size=16, ratio=2.0):
    """Ostry piksmap także na ekranach HiDPI."""
    px = QPixmap(int(size * ratio), int(size * ratio))
    px.fill(Qt.GlobalColor.transparent)
    if QSvgRenderer is not None:
        renderer = QSvgRenderer(QByteArray(svg(name, color)))
        painter = QPainter(px)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter)
        painter.end()
    else:
        px.loadFromData(svg(name, color), "SVG")
    px.setDevicePixelRatio(ratio)
    return px


def icon(name, color, size=16):
    ic = QIcon()
    ic.addPixmap(pixmap(name, color, size))
    return ic


def qsize(n):
    return QSize(n, n)


def tinted_pixmap(path, color, size=16, ratio=2.0):
    """Ikona z pliku PNG (maska alfa) przebarwiona na kolor z palety wtyczki."""
    from qgis.PyQt.QtGui import QColor
    src = QPixmap(path).scaled(int(size * ratio), int(size * ratio), Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
    px = QPixmap(src.size())
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    painter.drawPixmap(0, 0, src)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(px.rect(), QColor(color))
    painter.end()
    px.setDevicePixelRatio(ratio)
    return px


def tinted_icon(path, color, size=16):
    ic = QIcon()
    ic.addPixmap(tinted_pixmap(path, color, size))
    return ic
