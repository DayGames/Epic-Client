"""A borderless (frameless) window base with a custom draggable title bar."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton
from PySide6.QtCore import Qt, QPoint

from ui.theme import app_logo_pixmap


class TitleBar(QFrame):
    """Custom title bar: logo + title on the left, minimize/close on the right.

    Handles window dragging since a frameless window has no OS title bar.
    """

    def __init__(self, window: QWidget, title: str):
        super().__init__()
        self.setObjectName("TitleBar")
        self.setFixedHeight(40)
        self._window = window
        self._drag_offset: QPoint | None = None

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 0, 8, 0)
        row.setSpacing(6)

        logo = QLabel()
        logo.setPixmap(app_logo_pixmap(20).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        row.addWidget(logo)

        self.title = QLabel(title)
        self.title.setObjectName("TitleBarTitle")
        row.addWidget(self.title)
        row.addStretch()

        self.min_btn = QPushButton("–")  # en dash
        self.min_btn.setObjectName("WinBtn")
        self.min_btn.clicked.connect(self._window.showMinimized)
        row.addWidget(self.min_btn)

        self.close_btn = QPushButton("✕")  # x
        self.close_btn.setObjectName("WinBtn")
        self.close_btn.setProperty("class", "close")
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.clicked.connect(self._window.close)
        row.addWidget(self.close_btn)

    # ---- window dragging ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_offset = None


class FramelessWindow(QWidget):
    """Base window: no OS border, rounded container, custom title bar.

    Subclasses add their widgets to ``self.body`` (a QVBoxLayout).
    """

    def __init__(self, title: str):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)  # lets the rounded corners show

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        container = QFrame()
        container.setObjectName("Container")
        outer.addWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.titlebar = TitleBar(self, title)
        root.addWidget(self.titlebar)

        content = QWidget()
        self.body = QVBoxLayout(content)
        self.body.setContentsMargins(18, 14, 18, 18)
        root.addWidget(content, 1)
