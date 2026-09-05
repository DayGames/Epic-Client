"""Thin wrapper around the backend HTTP API."""
import httpx

from config import SERVER_URL, DOWNLOAD_DIR


class ApiError(Exception):
    """Raised when the server returns an error."""


class ApiClient:
    def __init__(self, base_url: str = SERVER_URL):
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None

    # --- helpers ---
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @staticmethod
    def _detail(resp: httpx.Response) -> str:
        try:
            return resp.json().get("detail", resp.text)
        except Exception:
            return resp.text

    # --- auth ---
    def register(self, username: str, password: str) -> None:
        resp = httpx.post(
            f"{self.base_url}/users/register",
            json={"username": username, "password": password},
            timeout=30,
        )
        if resp.status_code >= 400:
            raise ApiError(self._detail(resp))

    def login(self, username: str, password: str) -> None:
        # OAuth2 password flow expects form-encoded data, not JSON.
        resp = httpx.post(
            f"{self.base_url}/users/login",
            data={"username": username, "password": password},
            timeout=30,
        )
        if resp.status_code >= 400:
            raise ApiError(self._detail(resp))
        self.token = resp.json()["access_token"]

    # --- apps ---
    def list_apps(self) -> list[dict]:
        resp = httpx.get(f"{self.base_url}/apps", timeout=30)
        if resp.status_code >= 400:
            raise ApiError(self._detail(resp))
        return resp.json()

    def upload_app(self, name: str, description: str, version: str, file_path: str) -> dict:
        with open(file_path, "rb") as f:
            resp = httpx.post(
                f"{self.base_url}/apps",
                data={"name": name, "description": description, "version": version},
                files={"file": (file_path.split("/")[-1], f)},
                headers=self._headers(),
                timeout=None,
            )
        if resp.status_code >= 400:
            raise ApiError(self._detail(resp))
        return resp.json()

    def download_app(self, app_id: int, save_name: str) -> str:
        """Streams the installer to DOWNLOAD_DIR; returns the saved path."""
        dest = DOWNLOAD_DIR / save_name
        with httpx.stream("GET", f"{self.base_url}/apps/{app_id}/download", timeout=None) as resp:
            if resp.status_code >= 400:
                raise ApiError(self._detail(resp))
            with dest.open("wb") as out:
                for chunk in resp.iter_bytes():
                    out.write(chunk)
        return str(dest)
