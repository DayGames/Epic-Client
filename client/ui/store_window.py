"""Main store window: browse, view media, download/play, edit, and manage DLC."""
import os
import sys
import zipfile
import subprocess

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QMessageBox, QInputDialog, QFrame, QScrollArea,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap

from api import ApiClient, ApiError
from ui.theme import placeholder_icon, icon_from_bytes
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
        os.startfile(path)  # noqa  (Windows only)
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


class StoreWindow(FramelessWindow):
    def __init__(self, api: ApiClient, username: str):
        super().__init__("Epic Store")
        self.api = api
        self.username = username
        self.apps: list[dict] = []
        self.downloaded: dict[int, str] = {}

        self.setFixedSize(1000, 640)
        root = self.body
        root.setSpacing(14)

        # Header
        header = QHBoxLayout()
        tbox = QVBoxLayout()
        title = QLabel("Epic Store"); title.setObjectName("Title")
        sub = QLabel(f"Signed in as {username}"); sub.setObjectName("Subtitle")
        tbox.addWidget(title); tbox.addWidget(sub)
        header.addLayout(tbox); header.addStretch()
        refresh = QPushButton("Refresh"); refresh.clicked.connect(self.load_apps)
        upload = QPushButton("Upload game"); upload.setObjectName("Primary")
        upload.clicked.connect(self.upload)
        header.addWidget(refresh); header.addWidget(upload)
        root.addLayout(header)

        # Body: list + details
        body = QHBoxLayout(); body.setSpacing(14)
        self.list = QListWidget()
        self.list.setIconSize(QSize(44, 44))
        self.list.setFixedWidth(300)
        self.list.currentRowChanged.connect(self.show_details)
        body.addWidget(self.list)

        # Scrollable details panel
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        panel = QFrame(); panel.setObjectName("Panel")
        self.detail_layout = QVBoxLayout(panel)
        self.detail_layout.setContentsMargins(20, 20, 20, 20)
        self.detail_layout.setSpacing(12)
        self.scroll.setWidget(panel)
        body.addWidget(self.scroll, 1)
        root.addLayout(body)

        self.load_apps()

    # ---------- data ----------
    def load_apps(self):
        try:
            self.apps = self.api.list_apps()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load games:\n{e}")
            return
        self.list.clear()
        if not self.apps:
            empty = QListWidgetItem("  No games yet.\n  Click “Upload game” to add one.")
            empty.setFlags(Qt.NoItemFlags)
            self.list.addItem(empty)
            self._show_placeholder()
            return
        for app in self.apps:
            item = QListWidgetItem(f"  {app['name']}\n  by {app['owner_username']}")
            item.setIcon(self._icon_for(app))
            self.list.addItem(item)
        self._show_placeholder()

    def _icon_for(self, app: dict):
        if app.get("has_icon"):
            data = self.api.get_icon_bytes(app["id"])
            if data:
                icon = icon_from_bytes(data, 44)
                if not icon.isNull():
                    return icon
        return placeholder_icon(app["name"], 44)

    # ---------- details panel ----------
    def _clear_details(self):
        while self.detail_layout.count():
            item = self.detail_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                self._clear_sublayout(item.layout())

    def _clear_sublayout(self, lay):
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_sublayout(item.layout())

    def _show_placeholder(self):
        self._clear_details()
        msg = QLabel("Select a game to see details.")
        msg.setObjectName("Subtitle")
        self.detail_layout.addWidget(msg)
        self.detail_layout.addStretch()

    def show_details(self, row: int):
        if row < 0 or row >= len(self.apps):
            return
        app = self.apps[row]
        self._clear_details()

        # Header: icon + name + owner + meta
        head = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(self._icon_for(app).pixmap(72, 72))
        icon.setFixedSize(72, 72)
        head.addWidget(icon)
        nbox = QVBoxLayout(); nbox.addStretch()
        name = QLabel(app["name"]); name.setObjectName("SectionLabel")
        owner = QLabel(f"by {app['owner_username']}"); owner.setObjectName("Subtitle")
        meta = QLabel(f"Version {app['version']}  ·  {human_size(app['size_bytes'])}")
        meta.setObjectName("Subtitle")
        nbox.addWidget(name); nbox.addWidget(owner); nbox.addWidget(meta); nbox.addStretch()
        head.addLayout(nbox); head.addStretch()
        self.detail_layout.addLayout(head)

        # Description
        desc = QLabel(app["description"] or "No description provided.")
        desc.setWordWrap(True)
        self.detail_layout.addWidget(desc)

        # Screenshots
        images = [m for m in app.get("media", []) if m["kind"] == "image"]
        if images:
            self.detail_layout.addWidget(self._section_label("Screenshots"))
            row_l = QHBoxLayout()
            for m in images[:4]:
                data = self.api.get_media_bytes(app["id"], m["id"])
                if data:
                    pm = QPixmap(); pm.loadFromData(data)
                    if not pm.isNull():
                        thumb = QLabel()
                        thumb.setPixmap(pm.scaled(150, 84, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        row_l.addWidget(thumb)
            row_l.addStretch()
            self.detail_layout.addLayout(row_l)

        # Videos
        videos = [m for m in app.get("media", []) if m["kind"] == "video"]
        if videos:
            self.detail_layout.addWidget(self._section_label("Videos"))
            for i, m in enumerate(videos, 1):
                vrow = QHBoxLayout()
                vrow.addWidget(QLabel(f"▶  Trailer {i}"))
                vrow.addStretch()
                btn = QPushButton("Open")
                btn.clicked.connect(lambda _=False, aid=app["id"], mid=m["id"]: self.open_video(aid, mid))
                vrow.addWidget(btn)
                self.detail_layout.addLayout(vrow)

        # Action buttons
        actions = QHBoxLayout()
        dl = QPushButton("Download"); dl.setObjectName("Primary")
        dl.clicked.connect(lambda _=False, a=app: self.download(a))
        actions.addWidget(dl)
        target = self.downloaded.get(app["id"])
        openbtn = QPushButton("Play" if (target and target.lower().endswith(".exe")) else "Open")
        openbtn.setEnabled(bool(target))
        openbtn.clicked.connect(lambda _=False, a=app: self.open_game(a))
        actions.addWidget(openbtn)
        self.detail_layout.addLayout(actions)

        # Owner-only controls
        if app["owner_username"] == self.username:
            owner_row = QHBoxLayout()
            edit = QPushButton("Edit")
            edit.clicked.connect(lambda _=False, a=app: self.edit(a))
            add_dlc = QPushButton("Add DLC")
            add_dlc.clicked.connect(lambda _=False, a=app: self.add_dlc(a))
            owner_row.addWidget(edit); owner_row.addWidget(add_dlc); owner_row.addStretch()
            self.detail_layout.addLayout(owner_row)

        # DLC list
        dlc = app.get("dlc", [])
        if dlc:
            self.detail_layout.addWidget(self._section_label("DLC"))
            for d in dlc:
                drow = QHBoxLayout()
                drow.addWidget(QLabel(f"{d['name']}  ·  {human_size(d['size_bytes'])}"))
                drow.addStretch()
                get = QPushButton("Download")
                get.clicked.connect(lambda _=False, a=app, dd=d: self.download_dlc(a, dd))
                drow.addWidget(get)
                self.detail_layout.addLayout(drow)

        self.detail_layout.addStretch()

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: 600; margin-top: 4px;")
        return lbl

    # ---------- actions ----------
    def download(self, app: dict):
        try:
            zip_path = self.api.download_app(app["id"], f"{app['name']}-{app['version']}.zip")
            folder = extract_zip(zip_path)
        except zipfile.BadZipFile:
            QMessageBox.critical(self, "Download failed", "The downloaded file is not a valid .zip.")
            return
        except Exception as e:
            QMessageBox.critical(self, "Download failed", str(e))
            return
        target = find_exe(folder) or folder
        self.downloaded[app["id"]] = target
        label = "Run the game now?" if target != folder else "Open the folder now?"
        if QMessageBox.question(self, "Downloaded & extracted",
                                f"Extracted to:\n{folder}\n\n{label}") == QMessageBox.Yes:
            self._launch(target)
        self.show_details(self.list.currentRow())

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
        try:
            self.api.upload_app(v["name"], v["description"], v["zip"],
                                v["icon"], v["images"], v["videos"])
        except ApiError as e:
            QMessageBox.warning(self, "Upload failed", str(e)); return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e)); return
        QMessageBox.information(self, "Uploaded", f"'{v['name']}' is now in the store.")
        self.load_apps()

    def edit(self, app: dict):
        dlg = UploadDialog(self, mode="edit", app=app)
        if not dlg.exec():
            return
        v = dlg.values()
        try:
            self.api.edit_app(app["id"], v["name"], v["description"])
            if v["images"] or v["videos"]:
                self.api.add_media(app["id"], v["images"], v["videos"])
        except ApiError as e:
            QMessageBox.warning(self, "Edit failed", str(e)); return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e)); return
        QMessageBox.information(self, "Saved", "Your changes were saved.")
        self.load_apps()

    def add_dlc(self, app: dict):
        from PySide6.QtWidgets import QFileDialog
        name, ok = QInputDialog.getText(self, "DLC name", "Name of the DLC:")
        if not ok or not name.strip():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Choose DLC .zip", "", "Zip archives (*.zip)")
        if not path:
            return
        if not path.lower().endswith(".zip"):
            QMessageBox.warning(self, "Zip required", "DLC must be a .zip file."); return
        try:
            self.api.add_dlc(app["id"], name.strip(), path)
        except ApiError as e:
            QMessageBox.warning(self, "DLC upload failed", str(e)); return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e)); return
        QMessageBox.information(self, "DLC added", f"'{name}' was added to {app['name']}.")
        self.load_apps()
