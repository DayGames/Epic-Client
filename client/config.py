"""Client-side settings."""
import json
from pathlib import Path

# Where the backend lives. Change to your deployed URL later.
SERVER_URL = "http://127.0.0.1:8000"

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
