"""Main store window: browse, download, and upload apps."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QMessageBox, QFileDialog, QInputDialog, QTextEdit,
)
from PySide6.QtCore import Qt

from api import ApiClient, ApiError


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


class StoreWindow(QWidget):
    def __init__(self, api: ApiClient, username: str):
        super().__init__()
        self.api = api
        self.apps: list[dict] = []

        self.setWindowTitle(f"Epic Client — {username}")
        self.resize(700, 480)

        root = QVBoxLayout(self)

        # Top bar
        top = QHBoxLayout()
        top.addWidget(QLabel("<b>Store</b>"))
        top.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_apps)
        upload_btn = QPushButton("Upload app")
        upload_btn.clicked.connect(self.upload)
        top.addWidget(refresh_btn)
        top.addWidget(upload_btn)
        root.addLayout(top)

        # Main split: list on left, details on right
        body = QHBoxLayout()

        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.show_details)
        body.addWidget(self.list, 2)

        right = QVBoxLayout()
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        right.addWidget(self.details)
        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.download)
        self.download_btn.setEnabled(False)
        right.addWidget(self.download_btn)
        body.addLayout(right, 3)

        root.addLayout(body)

        self.load_apps()

    def load_apps(self):
        try:
            self.apps = self.api.list_apps()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load apps:\n{e}")
            return
        self.list.clear()
        for app in self.apps:
            item = QListWidgetItem(f"{app['name']}  (v{app['version']})")
            self.list.addItem(item)
        self.details.clear()
        self.download_btn.setEnabled(False)

    def show_details(self, row: int):
        if row < 0 or row >= len(self.apps):
            self.download_btn.setEnabled(False)
            return
        app = self.apps[row]
        self.details.setHtml(
            f"<h2>{app['name']}</h2>"
            f"<p><b>Version:</b> {app['version']}</p>"
            f"<p><b>Size:</b> {human_size(app['size_bytes'])}</p>"
            f"<p>{app['description'] or '<i>No description.</i>'}</p>"
        )
        self.download_btn.setEnabled(True)

    def download(self):
        row = self.list.currentRow()
        if row < 0:
            return
        app = self.apps[row]
        try:
            path = self.api.download_app(app["id"], f"{app['name']}-{app['version']}")
        except Exception as e:
            QMessageBox.critical(self, "Download failed", str(e))
            return
        QMessageBox.information(self, "Downloaded", f"Saved to:\n{path}")

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
        try:
            self.api.upload_app(name.strip(), description, version.strip(), file_path)
        except ApiError as e:
            QMessageBox.warning(self, "Upload failed", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        QMessageBox.information(self, "Uploaded", f"'{name}' is now in the store.")
        self.load_apps()
