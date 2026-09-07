"""Epic Client desktop app entry point.

Run from the client/ folder (with the backend already running):
    python main.py
"""
import sys
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

_CRASH_LOG = Path.home() / ".epicstore" / "client.log"


def _log_crash(exc_type, exc, tb) -> str:
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        _CRASH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _CRASH_LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"\n===== {datetime.now():%Y-%m-%d %H:%M:%S} =====\n{text}")
    except Exception:
        pass
    return text


def _install_crash_logging():
    """The windowed .exe has no console, so an unhandled exception would kill it
    silently. Log it and show a dialog instead — on the main thread and in QThreads."""
    def hook(exc_type, exc, tb):
        text = _log_crash(exc_type, exc, tb)
        try:
            QMessageBox.critical(None, "Epic Store — something went wrong",
                                 f"{exc_type.__name__}: {exc}\n\nDetails saved to:\n{_CRASH_LOG}")
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = hook
    try:
        import threading
        threading.excepthook = lambda a: _log_crash(a.exc_type, a.exc_value, a.exc_traceback)
    except Exception:
        pass

from api import ApiClient
from config import save_session, load_session, clear_session
from ui.login_window import LoginWindow
from ui.store_window import StoreWindow
from ui.theme import STYLESHEET, app_icon


class App:
    """Holds the windows so they aren't garbage-collected when we switch screens."""

    def __init__(self, deep_link_id: int | None = None):
        self.api = ApiClient()
        self.login: LoginWindow | None = None
        self.store: StoreWindow | None = None
        self.deep_link_id = deep_link_id  # game to open after login (from epicstore://)

    def on_login(self, username: str, remember: bool = True):
        if remember:
            save_session(username, self.api.token)  # remember for next launch
        self.store = StoreWindow(self.api, username, on_logout=self.on_logout)
        self.store.show()
        if self.deep_link_id is not None:
            self.store.open_game_by_id(self.deep_link_id)
            self.deep_link_id = None
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


def _register_protocol():
    """Register the epicstore:// URL scheme so a website's Download button opens us."""
    if not sys.platform.startswith("win") or not getattr(sys, "frozen", False):
        return  # only the built .exe can be the protocol target
    try:
        import winreg
        exe = sys.executable
        base = r"Software\Classes\epicstore"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "URL:EpicStore Protocol")
            winreg.SetValueEx(k, "URL Protocol", 0, winreg.REG_SZ, "")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\shell\open\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, f'"{exe}" "%1"')
    except Exception:
        pass


def parse_deeplink(argv) -> int | None:
    """Return the game id from an epicstore://game/<id> argument, if present."""
    for arg in argv[1:]:
        if arg.startswith("epicstore://game/"):
            try:
                return int(arg.rstrip("/").rsplit("/", 1)[-1])
            except ValueError:
                return None
    return None


def main():
    _install_crash_logging()
    _set_windows_app_id()
    _register_protocol()
    qt_app = QApplication(sys.argv)
    qt_app.setStyleSheet(STYLESHEET)
    qt_app.setWindowIcon(app_icon())
    app = App(deep_link_id=parse_deeplink(sys.argv))
    app.start()
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
