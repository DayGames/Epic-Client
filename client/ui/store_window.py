"""Main store window: browse (with icons), download, open, and upload apps."""
import os
import sys
import subprocess

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QMessageBox, QFileDialog, QInputDialog, QTextEdit, QFrame,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap

from api import ApiClient, ApiError
from ui.theme import placeholder_icon, icon_from_bytes
from ui.frameless import FramelessWindow


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def open_file(path: str):
    """Launch a downloaded file with the OS default handler."""
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: type ignore  (Windows only)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


class StoreWindow(FramelessWindow):
    def __init__(self, api: ApiClient, username: str):
        super().__init__("Epic Store")
        self.api = api
        self.apps: list[dict] = []
        self.downloaded: dict[int, str] = {}  # app_id -> saved path (this session)

        self.setFixedSize(900, 580)

        root = self.body  # add everything into the frameless content area
        root.setSpacing(14)

        # ---- Header ----
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Epic Store")
        title.setObjectName("Title")
        subtitle = QLabel(f"Signed in as {username}")
        subtitle.setObjectName("Subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_apps)
        upload_btn = QPushButton("Upload app")
        upload_btn.setObjectName("Primary")
        upload_btn.clicked.connect(self.upload)
        header.addWidget(refresh_btn)
        header.addWidget(upload_btn)
        root.addLayout(header)

        # ---- Body: list (left) + details (right) ----
        body = QHBoxLayout()
        body.setSpacing(14)

        self.list = QListWidget()
        self.list.setIconSize(QSize(44, 44))
        self.list.setMinimumWidth(300)
        self.list.currentRowChanged.connect(self.show_details)
        body.addWidget(self.list, 2)

        # Details panel
        panel = QFrame()
        panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(12)

        icon_row = QHBoxLayout()
        self.detail_icon = QLabel()
        self.detail_icon.setFixedSize(72, 72)
        self.detail_icon.setAlignment(Qt.AlignCenter)
        icon_row.addWidget(self.detail_icon)

        name_box = QVBoxLayout()
        self.detail_name = QLabel("Select an app")
        self.detail_name.setObjectName("SectionLabel")
        self.detail_meta = QLabel("")
        self.detail_meta.setObjectName("Subtitle")
        name_box.addStretch()
        name_box.addWidget(self.detail_name)
        name_box.addWidget(self.detail_meta)
        name_box.addStretch()
        icon_row.addLayout(name_box)
        icon_row.addStretch()
        panel_layout.addLayout(icon_row)

        self.detail_desc = QTextEdit()
        self.detail_desc.setReadOnly(True)
        panel_layout.addWidget(self.detail_desc, 1)

        btn_row = QHBoxLayout()
        self.download_btn = QPushButton("Download")
        self.download_btn.setObjectName("Primary")
        self.download_btn.clicked.connect(self.download)
        self.download_btn.setEnabled(False)
        self.open_btn = QPushButton("Open")
        self.open_btn.clicked.connect(self.open_selected)
        self.open_btn.setEnabled(False)
        btn_row.addWidget(self.download_btn)
        btn_row.addWidget(self.open_btn)
        panel_layout.addLayout(btn_row)

        body.addWidget(panel, 3)
        root.addLayout(body)

        self.load_apps()

    # ---- data ----
    def load_apps(self):
        try:
            self.apps = self.api.list_apps()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load apps:\n{e}")
            return
        self.list.clear()
        if not self.apps:
            empty = QListWidgetItem("  No apps yet.\n  Click “Upload app” to add one.")
            empty.setFlags(Qt.NoItemFlags)  # not selectable
            self.list.addItem(empty)
            self._clear_details()
            return
        for app in self.apps:
            item = QListWidgetItem(f"  {app['name']}\n  v{app['version']}")
            item.setIcon(self._icon_for(app))
            self.list.addItem(item)
        self._clear_details()

    def _icon_for(self, app: dict):
        """Real icon if the app has one, otherwise a colored letter tile."""
        if app.get("has_icon"):
            data = self.api.get_icon_bytes(app["id"])
            if data:
                icon = icon_from_bytes(data, 44)
                if not icon.isNull():
                    return icon
        return placeholder_icon(app["name"], 44)

    # ---- details ----
    def _clear_details(self):
        self.detail_name.setText("Select an app")
        self.detail_meta.setText("")
        self.detail_desc.clear()
        self.detail_icon.clear()
        self.download_btn.setEnabled(False)
        self.open_btn.setEnabled(False)

    def show_details(self, row: int):
        if row < 0 or row >= len(self.apps):
            self._clear_details()
            return
        app = self.apps[row]
        self.detail_name.setText(app["name"])
        self.detail_meta.setText(f"Version {app['version']}  ·  {human_size(app['size_bytes'])}")
        self.detail_desc.setPlainText(app["description"] or "No description provided.")

        pm = self._icon_for(app).pixmap(72, 72)
        self.detail_icon.setPixmap(pm)

        self.download_btn.setEnabled(True)
        self.open_btn.setEnabled(app["id"] in self.downloaded)

    # ---- actions ----
    def download(self):
        row = self.list.currentRow()
        if row < 0:
            return
        app = self.apps[row]
        self.download_btn.setEnabled(False)
        self.download_btn.setText("Downloading…")
        try:
            path = self.api.download_app(app["id"], f"{app['name']}-{app['version']}")
        except Exception as e:
            QMessageBox.critical(self, "Download failed", str(e))
            return
        finally:
            self.download_btn.setText("Download")
            self.download_btn.setEnabled(True)

        self.downloaded[app["id"]] = path
        self.open_btn.setEnabled(True)

        answer = QMessageBox.question(
            self, "Downloaded",
            f"Saved to:\n{path}\n\nOpen it now?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self._launch(path)

    def open_selected(self):
        row = self.list.currentRow()
        if row < 0:
            return
        path = self.downloaded.get(self.apps[row]["id"])
        if path and os.path.exists(path):
            self._launch(path)
        else:
            QMessageBox.information(self, "Not downloaded", "Download the app first.")

    def _launch(self, path: str):
        try:
            open_file(path)
        except Exception as e:
            QMessageBox.critical(self, "Could not open", str(e))

    def upload(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose installer file")
        if not file_path:
            return
        name, ok = QInputDialog.getText(self, "App name", "Name:")
        if not ok or not name.strip():
            return
        version, ok = QInputDialog.getText(self, "Version", "Version:", text="1.0.0")
        if not ok:
            return
        description, ok = QInputDialog.getMultiLineText(self, "Description", "Description:")
        if not ok:
            return
        # Optional icon
        icon_path, _ = QFileDialog.getOpenFileName(
            self, "Choose an icon (optional — Cancel to skip)",
            "", "Images (*.png *.jpg *.jpeg *.ico *.bmp)",
        )
        try:
            self.api.upload_app(
                name.strip(), description, version.strip(), file_path,
                icon_path or None,
            )
        except ApiError as e:
            QMessageBox.warning(self, "Upload failed", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        QMessageBox.information(self, "Uploaded", f"'{name}' is now in the store.")
        self.load_apps()
