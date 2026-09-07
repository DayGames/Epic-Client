"""Epic-Games-Store-style storefront: sidebar, top bar, hero, and a game grid."""
import os
import sys
import zipfile
import subprocess

import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QLineEdit,
    QMessageBox, QInputDialog, QFrame, QScrollArea, QStackedWidget, QButtonGroup,
    QFileDialog, QMenu, QProgressBar,
)
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QPixmap, QIcon

from api import ApiClient, ApiError
from ui.theme import (
    placeholder_icon, icon_from_bytes, gradient_pixmap, avatar_pixmap,
    app_logo_pixmap, rounded_pixmap_from_bytes,
)
from ui.frameless import FramelessWindow
from ui.upload_dialog import UploadDialog


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def open_file(path: str):
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def extract_zip(zip_path: str) -> str:
    folder = os.path.splitext(zip_path)[0]
    os.makedirs(folder, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(folder)
    return folder


def find_exe(folder: str) -> str | None:
    for root, _dirs, files in os.walk(folder):
        for name in files:
            if name.lower().endswith(".exe"):
                return os.path.join(root, name)
    return None


class ClickableFrame(QFrame):
    def __init__(self, on_click):
        super().__init__()
        self._cb = on_click
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._cb()


class DownloadWorker(QThread):
    """Downloads + extracts a game off the UI thread, reporting 0-100% progress."""
    progress = Signal(int)
    status = Signal(str)
    done = Signal(str)      # extracted folder path
    failed = Signal(str)

    def __init__(self, api, app):
        super().__init__()
        self.api = api
        self.app = app

    def run(self):
        try:
            self.status.emit("Downloading…")
            zip_path = self.api.download_app(
                self.app["id"],
                f"{self.app['name']}-{self.app['version']}.zip",
                self._on_progress,
            )
            self.status.emit("Extracting…")
            folder = self._extract(zip_path)
            self.done.emit(folder)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))

    def _on_progress(self, done, total):
        if total > 0:
            self.progress.emit(int(done / total * 50))  # download is first half

    def _extract(self, zip_path: str) -> str:
        folder = os.path.splitext(zip_path)[0]
        os.makedirs(folder, exist_ok=True)
        with zipfile.ZipFile(zip_path) as z:
            infos = z.infolist()
            n = max(1, len(infos))
            for i, info in enumerate(infos):
                z.extract(info, folder)
                self.progress.emit(50 + int((i + 1) / n * 50))  # extract is second half
        return folder


class UploadWorker(QThread):
    """Runs a blocking API call (upload / edit / add-DLC) off the UI thread so
    the window never freezes during a large upload to a remote server."""
    done = Signal(object)   # result of the callable
    failed = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self._fn = fn

    def run(self):
        try:
            self.done.emit(self._fn())
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))


class StoreWindow(FramelessWindow):
    def __init__(self, api: ApiClient, username: str, on_logout=None):
        super().__init__("Epic Store")
        self.api = api
        self.username = username
        self.on_logout = on_logout
        self._worker = None
        self._task = None        # background upload/edit worker (kept from GC)
        self._busy = None        # modal "please wait" dialog while a task runs
        self.current_app: dict | None = None
        self.apps: list[dict] = []
        self.downloaded: dict[int, str] = self._load_installed()  # persisted across runs
        self.view = "store"        # "store" | "library"
        self.search_text = ""
        self._banner_cache: dict[int, bytes | None] = {}

        self.setFixedSize(1200, 720)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(0)

        self._build_topbar()
        self._build_main()
        self.load_apps()

    # ---------- chrome ----------
    def _build_topbar(self):
        bar = QWidget()
        bar.setFixedHeight(64)
        row = QHBoxLayout(bar)
        row.setContentsMargins(20, 10, 20, 10)
        row.setSpacing(16)

        logo = QLabel()
        logo.setPixmap(app_logo_pixmap(30).scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        row.addWidget(logo)
        wordmark = QLabel("EPIC"); wordmark.setObjectName("Logo")
        row.addWidget(wordmark)

        self.search = QLineEdit()
        self.search.setObjectName("Search")
        self.search.setPlaceholderText("Search store")
        self.search.setFixedWidth(300)
        self.search.textChanged.connect(self._on_search)
        row.addWidget(self.search)

        # decorative top links
        self.top_group = QButtonGroup(self)
        for i, name in enumerate(("Discover", "Browse", "News")):
            b = QPushButton(name); b.setObjectName("TopLink"); b.setCheckable(True)
            b.setChecked(i == 0)
            b.clicked.connect(lambda _=False, n=name: self._top_link(n))
            self.top_group.addButton(b)
            row.addWidget(b)

        row.addStretch()
        avatar = QPushButton()
        avatar.setObjectName("Avatar")
        avatar.setIcon(QIcon(avatar_pixmap(self.username, 34)))
        avatar.setIconSize(QSize(34, 34))
        avatar.setToolTip(self.username)
        avatar.setCursor(Qt.PointingHandCursor)
        menu = QMenu(avatar)
        menu.addAction(f"Signed in as {self.username}").setEnabled(False)
        menu.addSeparator()
        menu.addAction("Log out", self._logout)
        avatar.setMenu(menu)
        row.addWidget(avatar)

        self.body.addWidget(bar)

    def _logout(self):
        if self.on_logout:
            self.on_logout()

    def _build_main(self):
        main = QHBoxLayout()
        main.setContentsMargins(14, 0, 14, 14)
        main.setSpacing(14)

        # Sidebar
        side = QWidget(); side.setObjectName("Sidebar"); side.setFixedWidth(200)
        sl = QVBoxLayout(side); sl.setContentsMargins(6, 6, 6, 6); sl.setSpacing(6)
        self.nav_group = QButtonGroup(self)
        self.nav_store = self._nav("🛍  Store", True, lambda: self._set_view("store"))
        self.nav_library = self._nav("📚  Library", False, lambda: self._set_view("library"))
        sl.addWidget(self.nav_store)
        sl.addWidget(self.nav_library)
        sl.addStretch()
        upload = QPushButton("Upload game"); upload.setObjectName("Primary")
        upload.clicked.connect(self.upload)
        sl.addWidget(upload)
        main.addWidget(side)

        # Content stack
        self.stack = QStackedWidget()
        # page 0: store scroll
        self.store_scroll = QScrollArea(); self.store_scroll.setWidgetResizable(True)
        self.store_scroll.setFrameShape(QFrame.NoFrame)
        self.store_page = QWidget()
        self.store_layout = QVBoxLayout(self.store_page)
        self.store_layout.setContentsMargins(6, 6, 6, 6)
        self.store_layout.setSpacing(18)
        self.store_scroll.setWidget(self.store_page)
        self.stack.addWidget(self.store_scroll)
        # page 1: detail scroll
        self.detail_scroll = QScrollArea(); self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setFrameShape(QFrame.NoFrame)
        self.detail_page = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_page)
        self.detail_layout.setContentsMargins(6, 6, 6, 6)
        self.detail_layout.setSpacing(14)
        self.detail_scroll.setWidget(self.detail_page)
        self.stack.addWidget(self.detail_scroll)

        main.addWidget(self.stack, 1)
        self.body.addLayout(main)

    def _nav(self, text, checked, cb):
        b = QPushButton(text); b.setObjectName("NavItem"); b.setCheckable(True)
        b.setChecked(checked)
        b.clicked.connect(cb)
        self.nav_group.addButton(b)
        return b

    # ---------- events ----------
    def _on_search(self, text):
        self.search_text = text.strip().lower()
        self.render_store()

    def _top_link(self, name):
        if name == "News":
            QMessageBox.information(self, "News", "No news yet — check back later!")
            # revert selection to Discover
            self.top_group.buttons()[0].setChecked(True)
            return
        self._set_view("store")

    def _set_view(self, view):
        self.view = view
        self.nav_store.setChecked(view == "store")
        self.nav_library.setChecked(view == "library")
        self.stack.setCurrentIndex(0)
        self.render_store()

    # ---------- installed-state persistence ----------
    def _installed_file(self):
        from config import DOWNLOAD_DIR
        return DOWNLOAD_DIR / "installed.json"

    def _load_installed(self) -> dict[int, str]:
        """Load the map of downloaded games, dropping any whose files are gone."""
        try:
            data = json.loads(self._installed_file().read_text())
            return {int(k): v for k, v in data.items() if os.path.exists(v)}
        except Exception:
            return {}

    def _save_installed(self):
        try:
            self._installed_file().write_text(json.dumps(self.downloaded))
        except Exception:
            pass

    # ---------- data ----------
    def load_apps(self):
        try:
            self.apps = self.api.list_apps()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load games:\n{e}")
            return
        self.render_store()

    def _visible_apps(self) -> list[dict]:
        apps = self.apps
        if self.view == "library":
            apps = [a for a in apps if a["id"] in self.downloaded]
        if self.search_text:
            apps = [a for a in apps
                    if self.search_text in a["name"].lower()
                    or self.search_text in a["owner_username"].lower()]
        return apps

    def _banner_bytes(self, app: dict) -> bytes | None:
        """First screenshot bytes (cached) for cards/hero, else None."""
        if app["id"] in self._banner_cache:
            return self._banner_cache[app["id"]]
        data = None
        images = [m for m in app.get("media", []) if m["kind"] == "image"]
        if images:
            data = self.api.get_media_bytes(app["id"], images[0]["id"])
        elif app.get("has_icon"):
            data = self.api.get_icon_bytes(app["id"])
        self._banner_cache[app["id"]] = data
        return data

    def _banner_pixmap(self, app: dict, w: int, h: int) -> QPixmap:
        data = self._banner_bytes(app)
        if data:
            pm = rounded_pixmap_from_bytes(data, w, h, 10)
            if pm:
                return pm
        return gradient_pixmap(app["name"], w, h)

    # ---------- store page ----------
    def _clear(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear(item.layout())

    def render_store(self):
        self._clear(self.store_layout)
        apps = self._visible_apps()

        if not apps:
            box = QVBoxLayout()
            t = QLabel("Your library is empty." if self.view == "library"
                       else "No games in the store yet.")
            t.setObjectName("SectionLabel")
            s = QLabel("Downloaded games appear here." if self.view == "library"
                       else "Click “Upload game” to add the first one.")
            s.setObjectName("Subtitle")
            self.store_layout.addWidget(t)
            self.store_layout.addWidget(s)
            self.store_layout.addStretch()
            return

        # Featured hero = first game (only on store view without search)
        start = 0
        if self.view == "store" and not self.search_text:
            self.store_layout.addWidget(self._make_hero(apps[0]))
            heading = QLabel("Browse"); heading.setObjectName("SectionLabel")
            self.store_layout.addWidget(heading)

        # Grid of cards
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(14)
        cols = 3
        for i, app in enumerate(apps):
            grid.addWidget(self._make_card(app), i // cols, i % cols)
        # keep cards left-aligned
        for c in range(cols):
            grid.setColumnStretch(c, 1)
        self.store_layout.addWidget(grid_host)
        self.store_layout.addStretch()

    def _make_hero(self, app: dict) -> QWidget:
        hero = ClickableFrame(lambda a=app: self.open_detail(a))
        hero.setObjectName("Hero")
        hero.setFixedHeight(250)
        hero.setStyleSheet("")  # use image as content
        lay = QHBoxLayout(hero)
        lay.setContentsMargins(0, 0, 0, 0)

        img = QLabel()
        img.setPixmap(self._banner_pixmap(app, 1000, 250))
        img.setFixedHeight(250)
        lay.addWidget(img)

        # overlay text
        overlay = QWidget(hero)
        overlay.setStyleSheet("background: transparent;")
        ol = QVBoxLayout(overlay)
        ol.setContentsMargins(36, 0, 36, 0)
        ol.addStretch()
        tag = QLabel("FEATURED"); tag.setObjectName("Subtitle")
        title = QLabel(app["name"]); title.setObjectName("HeroTitle")
        owner = QLabel(f"by {app['owner_username']}"); owner.setObjectName("Subtitle")
        view = QPushButton("View"); view.setObjectName("Primary"); view.setFixedWidth(120)
        view.clicked.connect(lambda _=False, a=app: self.open_detail(a))
        ol.addWidget(tag); ol.addWidget(title); ol.addWidget(owner)
        ol.addSpacing(10); ol.addWidget(view)
        ol.addStretch()
        overlay.setGeometry(0, 0, 980, 250)
        return hero

    def _make_card(self, app: dict) -> QFrame:
        card = ClickableFrame(lambda a=app: self.open_detail(a))
        card.setObjectName("GameCard")
        card.setFixedHeight(220)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        thumb = QLabel()
        thumb.setPixmap(self._banner_pixmap(app, 320, 150).scaled(320, 150, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        thumb.setFixedHeight(150)
        lay.addWidget(thumb)

        name = QLabel(app["name"]); name.setObjectName("CardTitle")
        owner = QLabel(f"by {app['owner_username']}"); owner.setObjectName("CardSub")
        lay.addWidget(name); lay.addWidget(owner)
        return card

    # ---------- detail page ----------
    def open_game_by_id(self, app_id: int):
        """Open a specific game's page (used by the epicstore:// deep link)."""
        for a in self.apps:
            if a["id"] == app_id:
                self.open_detail(a)
                return

    def open_detail(self, app: dict):
        self.current_app = app
        self._clear(self.detail_layout)

        back = QPushButton("←  Back to store")
        back.setFixedWidth(160)
        back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.detail_layout.addWidget(back)

        banner = QLabel()
        banner.setPixmap(self._banner_pixmap(app, 940, 300))
        self.detail_layout.addWidget(banner)

        title = QLabel(app["name"]); title.setObjectName("Title")
        self.detail_layout.addWidget(title)
        owner = QLabel(f"by {app['owner_username']}   ·   Version {app['version']}   ·   {human_size(app['size_bytes'])}")
        owner.setObjectName("Subtitle")
        self.detail_layout.addWidget(owner)

        # actions — once installed, the Download button is replaced by Play/Open
        actions = QHBoxLayout()
        target = self.downloaded.get(app["id"])
        self._dl_btn = None
        if target:
            openbtn = QPushButton("Play" if target.lower().endswith(".exe") else "Open")
            openbtn.setObjectName("Primary")
            openbtn.clicked.connect(lambda _=False, a=app: self.open_game(a))
            actions.addWidget(openbtn)
            installed = QLabel("✓ Installed"); installed.setObjectName("Subtitle")
            actions.addWidget(installed)
        else:
            self._dl_btn = QPushButton("Download"); self._dl_btn.setObjectName("Primary")
            self._dl_btn.clicked.connect(lambda _=False, a=app: self.download(a))
            actions.addWidget(self._dl_btn)

        actions.addStretch()

        # owner-only 3-dots menu (Edit / Add DLC / Delete)
        if app["owner_username"] == self.username:
            more = QPushButton("⋯"); more.setObjectName("MoreBtn")
            menu = QMenu(more)
            menu.addAction("Edit", lambda a=app: self.edit(a))
            menu.addAction("Add DLC", lambda a=app: self.add_dlc(a))
            menu.addSeparator()
            menu.addAction("Delete game", lambda a=app: self.delete_app(a))
            more.setMenu(menu)
            actions.addWidget(more)

        self.detail_layout.addLayout(actions)

        # progress row (hidden until a download starts)
        self._progress = QProgressBar()
        self._progress.setFixedWidth(340)
        self._progress.hide()
        self._progress_label = QLabel(""); self._progress_label.setObjectName("Subtitle")
        self._progress_label.hide()
        prow = QHBoxLayout()
        prow.addWidget(self._progress)
        prow.addWidget(self._progress_label)
        prow.addStretch()
        self.detail_layout.addLayout(prow)

        desc = QLabel(app["description"] or "No description provided.")
        desc.setWordWrap(True)
        self.detail_layout.addWidget(desc)

        images = [m for m in app.get("media", []) if m["kind"] == "image"]
        if images:
            self.detail_layout.addWidget(self._section("Screenshots"))
            r = QHBoxLayout()
            for m in images[:4]:
                data = self.api.get_media_bytes(app["id"], m["id"])
                if data:
                    pm = QPixmap(); pm.loadFromData(data)
                    if not pm.isNull():
                        lbl = QLabel()
                        lbl.setPixmap(pm.scaled(200, 112, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        r.addWidget(lbl)
            r.addStretch()
            self.detail_layout.addLayout(r)

        videos = [m for m in app.get("media", []) if m["kind"] == "video"]
        if videos:
            self.detail_layout.addWidget(self._section("Videos"))
            for i, m in enumerate(videos, 1):
                vr = QHBoxLayout()
                vr.addWidget(QLabel(f"▶  Trailer {i}")); vr.addStretch()
                b = QPushButton("Open")
                b.clicked.connect(lambda _=False, aid=app["id"], mid=m["id"]: self.open_video(aid, mid))
                vr.addWidget(b)
                self.detail_layout.addLayout(vr)

        dlc = app.get("dlc", [])
        if dlc:
            self.detail_layout.addWidget(self._section("DLC"))
            for d in dlc:
                dr = QHBoxLayout()
                dr.addWidget(QLabel(f"{d['name']}   ·   {human_size(d['size_bytes'])}")); dr.addStretch()
                g = QPushButton("Download")
                g.clicked.connect(lambda _=False, a=app, dd=d: self.download_dlc(a, dd))
                dr.addWidget(g)
                self.detail_layout.addLayout(dr)

        self.detail_layout.addStretch()
        self.stack.setCurrentIndex(1)

    def _section(self, text):
        lbl = QLabel(text); lbl.setObjectName("SectionLabel")
        return lbl

    # ---------- actions ----------
    def download(self, app: dict):
        if self._worker and self._worker.isRunning():
            return  # a download is already in progress
        if self._dl_btn:
            self._dl_btn.hide()
        self._progress.setValue(0)
        self._progress.show()
        self._progress_label.setText("Starting…")
        self._progress_label.show()

        self._worker = DownloadWorker(self.api, app)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.status.connect(self._progress_label.setText)
        self._worker.done.connect(lambda folder, a=app: self._download_done(a, folder))
        self._worker.failed.connect(self._download_failed)
        self._worker.start()

    def _download_done(self, app: dict, folder: str):
        target = find_exe(folder) or folder
        self.downloaded[app["id"]] = target
        self._save_installed()
        # re-render so the Download button becomes Play/Open
        if self.current_app and self.current_app["id"] == app["id"]:
            self.open_detail(app)
        label = "Run the game now?" if target != folder else "Open the folder now?"
        if QMessageBox.question(self, "Downloaded & extracted",
                                f"Extracted to:\n{folder}\n\n{label}") == QMessageBox.Yes:
            self._launch(target)

    def _download_failed(self, msg: str):
        if self._progress:
            self._progress.hide()
            self._progress_label.hide()
        if self._dl_btn:
            self._dl_btn.show()
        QMessageBox.critical(self, "Download failed", msg)

    def open_game(self, app: dict):
        target = self.downloaded.get(app["id"])
        if target and os.path.exists(target):
            self._launch(target)
        else:
            QMessageBox.information(self, "Not downloaded", "Download the game first.")

    def download_dlc(self, app: dict, dlc: dict):
        try:
            zip_path = self.api.download_dlc(app["id"], dlc["id"], f"{app['name']}-{dlc['name']}.zip")
            folder = extract_zip(zip_path)
        except Exception as e:
            QMessageBox.critical(self, "DLC download failed", str(e))
            return
        if QMessageBox.question(self, "DLC downloaded",
                                f"Extracted to:\n{folder}\n\nOpen the folder now?") == QMessageBox.Yes:
            self._launch(folder)

    def open_video(self, app_id: int, media_id: int):
        data = self.api.get_media_bytes(app_id, media_id)
        if not data:
            QMessageBox.critical(self, "Error", "Could not fetch the video.")
            return
        from config import DOWNLOAD_DIR
        path = str(DOWNLOAD_DIR / f"clip-{app_id}-{media_id}.mp4")
        with open(path, "wb") as f:
            f.write(data)
        self._launch(path)

    def _launch(self, path: str):
        try:
            open_file(path)
        except Exception as e:
            QMessageBox.critical(self, "Could not open", str(e))

    def upload(self):
        dlg = UploadDialog(self, mode="create")
        if not dlg.exec():
            return
        v = dlg.values()
        self._run_task(
            lambda: self.api.upload_app(v["name"], v["description"], v["zip"],
                                        v["icon"], v["images"], v["videos"]),
            busy="Uploading game… large files can take a while.",
            on_done=lambda _r: self._upload_done(v["name"]),
            fail_title="Upload failed",
        )

    def _upload_done(self, name: str):
        QMessageBox.information(self, "Uploaded", f"'{name}' is now in the store.")
        self._banner_cache.clear()
        self.load_apps()

    # ---------- background task plumbing ----------
    def _run_task(self, fn, busy: str, on_done, fail_title: str):
        """Run a blocking API call on a worker thread with a modal busy dialog,
        so the window stays responsive instead of freezing (and looking crashed)."""
        if self._task and self._task.isRunning():
            QMessageBox.information(self, "Please wait", "Another upload is still running.")
            return
        self._begin_busy(busy)
        self._task = UploadWorker(fn)
        self._task.done.connect(lambda res: (self._end_busy(), on_done(res)))
        self._task.failed.connect(
            lambda msg: (self._end_busy(), QMessageBox.warning(self, fail_title, msg))
        )
        self._task.finished.connect(lambda: setattr(self, "_task", None))
        self._task.start()

    def _begin_busy(self, text: str):
        from PySide6.QtWidgets import QProgressDialog
        self._busy = QProgressDialog(text, None, 0, 0, self)   # 0..0 = indeterminate
        self._busy.setWindowTitle("Please wait")
        self._busy.setCancelButton(None)
        self._busy.setWindowModality(Qt.ApplicationModal)
        self._busy.setMinimumDuration(0)
        self._busy.setAutoClose(False)
        self._busy.setAutoReset(False)
        self._busy.show()

    def _end_busy(self):
        if self._busy is not None:
            self._busy.close()
            self._busy = None

    def edit(self, app: dict):
        dlg = UploadDialog(self, mode="edit", app=app)
        if not dlg.exec():
            return
        v = dlg.values()

        def work():
            self.api.edit_app(app["id"], v["name"], v["description"])
            if v["images"] or v["videos"]:
                self.api.add_media(app["id"], v["images"], v["videos"])

        def finished(_r):
            QMessageBox.information(self, "Saved", "Your changes were saved.")
            self._banner_cache.pop(app["id"], None)
            self.load_apps()

        self._run_task(work, busy="Saving changes…", on_done=finished,
                       fail_title="Edit failed")

    def delete_app(self, app: dict):
        if QMessageBox.warning(
            self, "Delete game",
            f"Permanently delete '{app['name']}'?\n\n"
            "This removes it from the store for everyone and cannot be undone.",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel,
        ) != QMessageBox.Yes:
            return

        app_id = app["id"]

        def finished(_r):
            QMessageBox.information(self, "Deleted", f"'{app['name']}' was removed.")
            self._banner_cache.pop(app_id, None)
            self.downloaded.pop(app_id, None)
            self._save_installed()
            self.current_app = None
            self.stack.setCurrentIndex(0)   # back to the store grid
            self.load_apps()                # refresh so the deleted game is gone

        self._run_task(lambda: self.api.delete_app(app_id),
                       busy=f"Deleting '{app['name']}'…",
                       on_done=finished, fail_title="Delete failed")

    def add_dlc(self, app: dict):
        name, ok = QInputDialog.getText(self, "DLC name", "Name of the DLC:")
        if not ok or not name.strip():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Choose DLC .zip", "", "Zip archives (*.zip)")
        if not path:
            return
        if not path.lower().endswith(".zip"):
            QMessageBox.warning(self, "Zip required", "DLC must be a .zip file."); return
        dlc_name = name.strip()
        self._run_task(
            lambda: self.api.add_dlc(app["id"], dlc_name, path),
            busy=f"Uploading DLC '{dlc_name}'…",
            on_done=lambda _r: (
                QMessageBox.information(self, "DLC added",
                                        f"'{dlc_name}' was added to {app['name']}."),
                self.load_apps(),
            ),
            fail_title="DLC upload failed",
        )
