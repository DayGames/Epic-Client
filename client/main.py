"""Epic Client desktop app entry point.

Run from the client/ folder (with the backend already running):
    python main.py
"""
import sys

from PySide6.QtWidgets import QApplication

from api import ApiClient
from config import save_session, load_session, clear_session
from ui.login_window import LoginWindow
from ui.store_window import StoreWindow
from ui.theme import STYLESHEET, app_icon


class App:
    """Holds the windows so they aren't garbage-collected when we switch screens."""

    def __init__(self):
        self.api = ApiClient()
        self.login: LoginWindow | None = None
        self.store: StoreWindow | None = None

    def on_login(self, username: str, remember: bool = True):
        if remember:
            save_session(username, self.api.token)  # remember for next launch
        self.store = StoreWindow(self.api, username, on_logout=self.on_logout)
        self.store.show()
        if self.login:
            self.login.close()
            self.login = None

    def on_logout(self):
        clear_session()
        self.api.token = None
        if self.store:
            self.store.close()
            self.store = None
        self._show_login()

    def _show_login(self):
        self.login = LoginWindow(self.api, self.on_login)
        self.login.show()

    def start(self):
        # Try to resume a remembered session before showing the login screen.
        sess = load_session()
        if sess:
            self.api.set_token(sess["token"])
            try:
                me = self.api.get_me()
                self.on_login(me["username"], remember=False)
                return
            except Exception:
                clear_session()
                self.api.token = None
        self._show_login()


def _set_windows_app_id():
    """Tell Windows this is its own app so the taskbar shows our icon, not Python's."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("EpicStore.Client.1")
        except Exception:
            pass


def main():
    _set_windows_app_id()
    qt_app = QApplication(sys.argv)
    qt_app.setStyleSheet(STYLESHEET)
    qt_app.setWindowIcon(app_icon())
    app = App()
    app.start()
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
