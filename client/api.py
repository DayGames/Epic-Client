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

    def upload_app(
        self,
        name: str,
        description: str,
        version: str,
        file_path: str,
        icon_path: str | None = None,
    ) -> dict:
        import os

        files = {"file": (os.path.basename(file_path), open(file_path, "rb"))}
        if icon_path:
            files["icon"] = (os.path.basename(icon_path), open(icon_path, "rb"))
        try:
            resp = httpx.post(
                f"{self.base_url}/apps",
                data={"name": name, "description": description, "version": version},
                files=files,
                headers=self._headers(),
                timeout=None,
            )
        finally:
            for _, (_, fh) in files.items():
                fh.close()
        if resp.status_code >= 400:
            raise ApiError(self._detail(resp))
        return resp.json()

    def get_icon_bytes(self, app_id: int) -> bytes | None:
        """Return an app's icon image bytes, or None if it has no icon."""
        try:
            resp = httpx.get(f"{self.base_url}/apps/{app_id}/icon", timeout=30)
        except Exception:
            return None
        if resp.status_code >= 400:
            return None
        return resp.content

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
