"""Client-side settings."""
from pathlib import Path

# Where the backend lives. Change to your deployed URL later.
SERVER_URL = "http://127.0.0.1:8000"

# Where downloaded installers are saved on this PC.
DOWNLOAD_DIR = Path.home() / "Downloads" / "EpicClient"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
