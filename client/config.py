"""Client-side settings."""
import os
import sys
import json
from pathlib import Path


def _app_dir() -> Path:
    # Folder the app runs from: next to the .exe when frozen, else this file's dir.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

# The public backend the shared .exe talks to.
# For an .exe you can send to other people this MUST be a public URL
# (e.g. your Railway domain) — localhost only works on the machine running the server.
# Priority: EPIC_STORE_SERVER env var  ->  a server.txt next to the app  ->  this default.
_DEFAULT_SERVER = "http://127.0.0.1:8000"   # <-- replace with your Railway URL, then rebuild


def _resolve_server_url() -> str:
    env = os.environ.get("EPIC_STORE_SERVER")
    if env:
        return env.strip()
    try:
        side_file = _app_dir() / "server.txt"
        if side_file.exists():
            txt = side_file.read_text().strip()
            if txt:
                return txt
    except Exception:
        pass
    return _DEFAULT_SERVER


SERVER_URL = _resolve_server_url()

# Where downloaded installers are saved on this PC.
DOWNLOAD_DIR = Path.home() / "Downloads" / "EpicClient"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Remembered-login file (username + token).
CONFIG_DIR = Path.home() / ".epicstore"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
SESSION_FILE = CONFIG_DIR / "session.json"


def save_session(username: str, token: str) -> None:
    try:
        SESSION_FILE.write_text(json.dumps({"username": username, "token": token}))
    except Exception:
        pass


def load_session() -> dict | None:
    try:
        data = json.loads(SESSION_FILE.read_text())
        if data.get("username") and data.get("token"):
            return data
    except Exception:
        pass
    return None


def clear_session() -> None:
    try:
        SESSION_FILE.unlink(missing_ok=True)
    except Exception:
        pass
