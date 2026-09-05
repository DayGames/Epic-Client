"""Shared visual theme: a modern dark stylesheet + icon helpers."""
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor, QFont, QBrush, QLinearGradient
from PySide6.QtCore import Qt, QRectF

# Colors
BG = "#14141f"
SURFACE = "#1e1e2e"
SURFACE_HI = "#2a2a3d"
BORDER = "#33334d"
TEXT = "#e6e6f0"
TEXT_DIM = "#9a9ab0"
ACCENT = "#7c5cff"
ACCENT_HI = "#9277ff"

STYLESHEET = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Segoe UI", sans-serif;
    font-size: 14px;
}}

/* Cards / panels */
#Card, #Panel {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

QLabel#Title {{
    font-size: 26px;
    font-weight: 700;
    color: {TEXT};
}}
QLabel#Subtitle {{
    color: {TEXT_DIM};
    font-size: 13px;
}}
QLabel#SectionLabel {{
    font-size: 16px;
    font-weight: 600;
}}

/* Inputs */
QLineEdit {{
    background-color: {SURFACE_HI};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 10px 12px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus {{
    border: 1px solid {ACCENT};
}}

/* Buttons */
QPushButton {{
    background-color: {SURFACE_HI};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: #34344a;
    border: 1px solid {ACCENT};
}}
QPushButton:disabled {{
    color: {TEXT_DIM};
    background-color: {SURFACE};
    border: 1px solid {BORDER};
}}
QPushButton#Primary {{
    background-color: {ACCENT};
    border: none;
    color: white;
}}
QPushButton#Primary:hover {{
    background-color: {ACCENT_HI};
}}
QPushButton#Primary:disabled {{
    background-color: #3a3357;
    color: {TEXT_DIM};
}}

/* App list */
QListWidget {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 6px;
    outline: 0;
}}
QListWidget::item {{
    border-radius: 8px;
    padding: 8px;
    margin: 2px 0;
}}
QListWidget::item:selected {{
    background-color: {ACCENT};
    color: white;
}}
QListWidget::item:hover:!selected {{
    background-color: {SURFACE_HI};
}}

QTextEdit {{
    background-color: transparent;
    border: none;
}}

/* Frameless window chrome */
#Container {{
    background-color: {BG};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
#TitleBar {{
    background-color: {SURFACE};
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
}}
#TitleBarTitle {{
    font-weight: 600;
    color: {TEXT_DIM};
    padding-left: 12px;
}}
QPushButton#WinBtn {{
    background: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 15px;
    color: {TEXT_DIM};
}}
QPushButton#WinBtn:hover {{
    background: {SURFACE_HI};
    color: {TEXT};
}}
QPushButton#CloseBtn:hover {{
    background: #e5484d;
    color: white;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""

# A rotating palette so placeholder icons aren't all the same color.
_PALETTE = ["#7c5cff", "#ff6b6b", "#4ecdc4", "#ffa94d", "#5c7cff", "#e879f9", "#34d399"]


def placeholder_icon(name: str, size: int = 48) -> QIcon:
    """Generate a rounded, colored tile showing the app's first letter."""
    letter = (name.strip()[:1] or "?").upper()
    color = QColor(_PALETTE[sum(ord(c) for c in name) % len(_PALETTE)])

    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0, color.lighter(120))
    grad.setColorAt(1, color.darker(115))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.24, size * 0.24)

    p.setPen(QColor("white"))
    font = QFont("Segoe UI", int(size * 0.42), QFont.Bold)
    p.setFont(font)
    p.drawText(pm.rect(), Qt.AlignCenter, letter)
    p.end()
    return QIcon(pm)


def app_logo_pixmap(size: int = 256) -> QPixmap:
    """The Epic Store brand mark: a rounded gradient tile with an 'E'."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0, QColor(ACCENT_HI))
    grad.setColorAt(1, QColor("#5b3ee0"))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.22, size * 0.22)
    p.setPen(QColor("white"))
    p.setFont(QFont("Segoe UI", int(size * 0.5), QFont.Black))
    p.drawText(pm.rect(), Qt.AlignCenter, "E")
    p.end()
    return pm


def app_icon() -> QIcon:
    """Runtime window/taskbar icon (no external file needed)."""
    return QIcon(app_logo_pixmap(256))


def icon_from_bytes(data: bytes, size: int = 48) -> QIcon:
    """Build a QIcon from raw image bytes (a downloaded icon)."""
    pm = QPixmap()
    pm.loadFromData(data)
    if pm.isNull():
        return QIcon()
    return QIcon(pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
