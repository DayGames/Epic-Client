"""Epic Client desktop app entry point.

Run from the client/ folder (with the backend already running):
    python main.py
"""
import sys

from PySide6.QtWidgets import QApplication

from api import ApiClient
from ui.login_window import LoginWindow
from ui.store_window import StoreWindow
from ui.theme import STYLESHEET


class App:
    """Holds the windows so they aren't garbage-collected when we switch screens."""

    def __init__(self):
        self.api = ApiClient()
        self.login = LoginWindow(self.api, self.on_login)
        self.store: StoreWindow | None = None

    def on_login(self, username: str):
        self.store = StoreWindow(self.api, username)
        self.store.show()
        self.login.close()

    def start(self):
        self.login.show()


def main():
    qt_app = QApplication(sys.argv)
    qt_app.setStyleSheet(STYLESHEET)
    app = App()
    app.start()
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
