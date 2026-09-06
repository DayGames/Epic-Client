"""Epic-Games-Store-style theme: dark chrome, sidebar, white CTAs."""
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor, QFont, QBrush, QLinearGradient
from PySide6.QtCore import Qt, QRectF

# Palette (close to the Epic Games launcher)
BG = "#0f0f13"          # app background (near black)
SURFACE = "#17171c"     # sidebar / cards
SURFACE_HI = "#26262d"  # hovered / raised
BORDER = "#2a2a32"
TEXT = "#f2f2f5"
TEXT_DIM = "#9a9aa6"
ACCENT = "#2f80ff"      # selection blue

STYLESHEET = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Segoe UI", sans-serif;
    font-size: 14px;
}}

#Card, #Panel {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

QLabel#Title {{ font-size: 26px; font-weight: 800; color: {TEXT}; }}
QLabel#Subtitle {{ color: {TEXT_DIM}; font-size: 13px; }}
QLabel#SectionLabel {{ font-size: 20px; font-weight: 700; }}
QLabel#HeroTitle {{ font-size: 30px; font-weight: 800; }}
QLabel#CardTitle {{ font-size: 14px; font-weight: 700; }}
QLabel#CardSub {{ color: {TEXT_DIM}; font-size: 12px; }}
QLabel#Logo {{ font-size: 18px; font-weight: 900; letter-spacing: 1px; }}

/* Inputs */
QLineEdit {{
    background-color: {SURFACE_HI};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 10px 12px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
QLineEdit#Search {{ border-radius: 18px; padding: 9px 18px; }}

/* Default buttons (secondary) */
QPushButton {{
    background-color: {SURFACE_HI};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: #32323b; }}
QPushButton:disabled {{ color: {TEXT_DIM}; background-color: {SURFACE}; }}

/* White call-to-action, like Epic's Buy/Get */
QPushButton#Primary {{
    background-color: #ffffff;
    border: none;
    color: #111116;
    border-radius: 8px;
    padding: 11px 22px;
    font-weight: 800;
}}
QPushButton#Primary:hover {{ background-color: #e2e2e8; }}
QPushButton#Primary:disabled {{ background-color: #3a3a42; color: {TEXT_DIM}; }}

/* Sidebar nav */
QWidget#Sidebar {{ background-color: {BG}; }}
QPushButton#NavItem {{
    background: transparent;
    border: none;
    text-align: left;
    padding: 11px 14px;
    border-radius: 10px;
    color: {TEXT_DIM};
    font-size: 15px;
    font-weight: 700;
}}
QPushButton#NavItem:hover {{ background: {SURFACE_HI}; color: {TEXT}; }}
QPushButton#NavItem:checked {{ background: {SURFACE_HI}; color: {TEXT}; }}

/* Top bar nav links */
QPushButton#TopLink {{
    background: transparent; border: none; color: {TEXT_DIM};
    font-size: 15px; font-weight: 700; padding: 6px 10px;
}}
QPushButton#TopLink:hover {{ color: {TEXT}; }}
QPushButton#TopLink:checked {{ color: {TEXT}; }}

/* Game cards */
QFrame#GameCard {{ background-color: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#GameCard:hover {{ border: 1px solid #4a4a55; }}
QFrame#Hero {{ border-radius: 16px; }}

QTextEdit {{ background-color: transparent; border: none; }}

/* 3-dots menu button + its popup */
QPushButton#MoreBtn {{ padding: 9px 14px; font-size: 18px; font-weight: 800; }}
QPushButton#MoreBtn::menu-indicator {{ image: none; width: 0; }}
QMenu {{ background-color: {SURFACE_HI}; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px; }}
QMenu::item {{ padding: 8px 22px; border-radius: 6px; color: {TEXT}; }}
QMenu::item:selected {{ background-color: {ACCENT}; color: white; }}

/* Download progress */
QProgressBar {{
    background-color: {SURFACE_HI};
    border: 1px solid {BORDER};
    border-radius: 9px;
    height: 18px;
    text-align: center;
    color: {TEXT};
    font-size: 12px;
}}
QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 9px; }}

/* Account avatar button */
QPushButton#Avatar {{ background: transparent; border: none; padding: 0; }}
QPushButton#Avatar::menu-indicator {{ image: none; width: 0; }}
#Container {{ background-color: {BG}; border: 1px solid {BORDER}; border-radius: 14px; }}
#TitleBar {{ background-color: {BG}; border-top-left-radius: 14px; border-top-right-radius: 14px; }}
#TitleBarTitle {{ font-weight: 600; color: {TEXT_DIM}; padding-left: 12px; }}
QPushButton#WinBtn {{ background: transparent; border: none; border-radius: 6px; padding: 4px 12px; font-size: 15px; color: {TEXT_DIM}; }}
QPushButton#WinBtn:hover {{ background: {SURFACE_HI}; color: {TEXT}; }}
QPushButton#CloseBtn:hover {{ background: #e5484d; color: white; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 5px; min-width: 24px; }}
"""

_PALETTE = ["#5b3ee0", "#c0392b", "#16a085", "#e67e22", "#2f80ff", "#c026d3", "#0f9d58"]


def _color_for(name: str) -> QColor:
    return QColor(_PALETTE[sum(ord(c) for c in name) % len(_PALETTE)])


def _rounded(size_w: int, size_h: int, color: QColor, letter: str, radius_ratio=0.2) -> QPixmap:
    pm = QPixmap(size_w, size_h)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, size_w, size_h)
    grad.setColorAt(0, color.lighter(125))
    grad.setColorAt(1, color.darker(120))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    r = min(size_w, size_h) * radius_ratio
    p.drawRoundedRect(QRectF(0, 0, size_w, size_h), r, r)
    if letter:
        p.setPen(QColor("white"))
        p.setFont(QFont("Segoe UI", int(min(size_w, size_h) * 0.42), QFont.Black))
        p.drawText(pm.rect(), Qt.AlignCenter, letter)
    p.end()
    return pm


def placeholder_icon(name: str, size: int = 48) -> QIcon:
    return QIcon(_rounded(size, size, _color_for(name), (name.strip()[:1] or "?").upper(), 0.24))


def gradient_pixmap(name: str, w: int, h: int) -> QPixmap:
    return _rounded(w, h, _color_for(name), (name.strip()[:1] or "?").upper(), 0.06)


def app_logo_pixmap(size: int = 256) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0, QColor("#2f80ff"))
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
    return QIcon(app_logo_pixmap(256))


def avatar_pixmap(letter: str, size: int = 34) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0, QColor("#c026d3"))
    grad.setColorAt(1, QColor("#7c3aed"))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    p.drawEllipse(0, 0, size, size)
    p.setPen(QColor("white"))
    p.setFont(QFont("Segoe UI", int(size * 0.45), QFont.Bold))
    p.drawText(pm.rect(), Qt.AlignCenter, (letter[:1] or "?").upper())
    p.end()
    return pm


def icon_from_bytes(data: bytes, size: int = 48) -> QIcon:
    pm = QPixmap()
    pm.loadFromData(data)
    if pm.isNull():
        return QIcon()
    return QIcon(pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))


def rounded_pixmap_from_bytes(data: bytes, w: int, h: int, radius: int = 10) -> QPixmap | None:
    """Scale/crop image bytes to fill w×h with rounded corners (for cards/heroes)."""
    src = QPixmap()
    src.loadFromData(data)
    if src.isNull():
        return None
    scaled = src.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    # center-crop
    x = max(0, (scaled.width() - w) // 2)
    y = max(0, (scaled.height() - h) // 2)
    scaled = scaled.copy(x, y, w, h)
    out = QPixmap(w, h)
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    path_pm = QPixmap(w, h)
    p.setBrush(QBrush(scaled))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)
    p.end()
    return out
