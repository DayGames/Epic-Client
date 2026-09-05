"""Central configuration for the Epic Client backend."""
from pathlib import Path
from pydantic_settings import BaseSettings

# Absolute path to the server/ directory so paths work no matter where you run from.
BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # --- Security ---
    # CHANGE THIS in production. Used to sign login tokens (JWT).
    secret_key: str = "change-me-to-a-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 day

    # --- Database ---
    database_url: str = f"sqlite:///{BASE_DIR / 'epicstore.db'}"

    # --- File storage (installers live here) ---
    files_dir: Path = BASE_DIR / "files"

    class Config:
        env_file = ".env"  # you can override any setting from a .env file


settings = Settings()

# Make sure the installer folder exists on startup.
settings.files_dir.mkdir(parents=True, exist_ok=True)
