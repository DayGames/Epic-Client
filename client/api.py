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

    def set_token(self, token: str) -> None:
        self.token = token

    def get_me(self) -> dict:
        """Validate the current token and return the logged-in user."""
        resp = httpx.get(f"{self.base_url}/users/me", headers=self._headers(), timeout=10)
        if resp.status_code >= 400:
            raise ApiError(self._detail(resp))
        return resp.json()

    # --- apps ---
    def list_apps(self) -> list[dict]:
        resp = httpx.get(f"{self.base_url}/apps", timeout=30)
        if resp.status_code >= 400:
            raise ApiError(self._detail(resp))
        return resp.json()

    @staticmethod
    def _file_tuples(field: str, paths: list[str] | None) -> list:
        """Build httpx multipart tuples for a list of files under one field name."""
        import os
        out = []
        for p in paths or []:
            out.append((field, (os.path.basename(p), open(p, "rb"))))
        return out

    def upload_app(
        self,
        name: str,
        description: str,
        file_path: str,
        icon_path: str | None = None,
        image_paths: list[str] | None = None,
        video_paths: list[str] | None = None,
    ) -> dict:
        import os

        files = [("file", (os.path.basename(file_path), open(file_path, "rb")))]
        if icon_path:
            files.append(("icon", (os.path.basename(icon_path), open(icon_path, "rb"))))
        files += self._file_tuples("images", image_paths)
        files += self._file_tuples("videos", video_paths)
        try:
            resp = httpx.post(
                f"{self.base_url}/apps",
                data={"name": name, "description": description},
                files=files,
                headers=self._headers(),
                timeout=None,
            )
        finally:
            for _, (_, fh) in files:
                fh.close()
        if resp.status_code >= 400:
            raise ApiError(self._detail(resp))
        return resp.json()

    def edit_app(self, app_id: int, name: str, description: str) -> dict:
        resp = httpx.patch(
            f"{self.base_url}/apps/{app_id}",
            data={"name": name, "description": description},
            headers=self._headers(),
            timeout=30,
        )
        if resp.status_code >= 400:
            raise ApiError(self._detail(resp))
        return resp.json()

    def add_media(
        self, app_id: int,
        image_paths: list[str] | None = None,
        video_paths: list[str] | None = None,
    ) -> dict:
        files = self._file_tuples("images", image_paths) + self._file_tuples("videos", video_paths)
        if not files:
            return {}
        try:
            resp = httpx.post(
                f"{self.base_url}/apps/{app_id}/media",
                files=files, headers=self._headers(), timeout=None,
            )
        finally:
            for _, (_, fh) in files:
                fh.close()
        if resp.status_code >= 400:
            raise ApiError(self._detail(resp))
        return resp.json()

    def add_dlc(self, app_id: int, name: str, zip_path: str) -> dict:
        import os
        with open(zip_path, "rb") as fh:
            resp = httpx.post(
                f"{self.base_url}/apps/{app_id}/dlc",
                data={"name": name},
                files={"file": (os.path.basename(zip_path), fh)},
                headers=self._headers(), timeout=None,
            )
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

    def get_media_bytes(self, app_id: int, media_id: int) -> bytes | None:
        try:
            resp = httpx.get(f"{self.base_url}/apps/{app_id}/media/{media_id}", timeout=30)
        except Exception:
            return None
        if resp.status_code >= 400:
            return None
        return resp.content

    def download_dlc(self, app_id: int, dlc_id: int, save_name: str) -> str:
        dest = DOWNLOAD_DIR / save_name
        with httpx.stream("GET", f"{self.base_url}/apps/{app_id}/dlc/{dlc_id}/download", timeout=None) as resp:
            if resp.status_code >= 400:
                raise ApiError(self._detail(resp))
            with dest.open("wb") as out:
                for chunk in resp.iter_bytes():
                    out.write(chunk)
        return str(dest)

    def download_app(self, app_id: int, save_name: str, on_progress=None) -> str:
        """Streams the installer to DOWNLOAD_DIR; returns the saved path.

        on_progress(bytes_done, total_bytes) is called as chunks arrive.
        """
        dest = DOWNLOAD_DIR / save_name
        with httpx.stream("GET", f"{self.base_url}/apps/{app_id}/download", timeout=None) as resp:
            if resp.status_code >= 400:
                raise ApiError(self._detail(resp))
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            with dest.open("wb") as out:
                for chunk in resp.iter_bytes():
                    out.write(chunk)
                    done += len(chunk)
                    if on_progress:
                        on_progress(done, total)
        return str(dest)
