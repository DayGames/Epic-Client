"""Dialog for uploading a new game or editing one you own."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt


class _FilePicker(QHBoxLayout):
    """A label + button that collects one or many file paths."""

    def __init__(self, button_text: str, filt: str, multi: bool = False):
        super().__init__()
        self.filt = filt
        self.multi = multi
        self.paths: list[str] = []

        self.status = QLabel("None selected")
        self.status.setObjectName("Subtitle")
        btn = QPushButton(button_text)
        btn.clicked.connect(self._pick)
        self.addWidget(self.status, 1)
        self.addWidget(btn)

    def _pick(self):
        if self.multi:
            paths, _ = QFileDialog.getOpenFileNames(None, "Choose files", "", self.filt)
        else:
            p, _ = QFileDialog.getOpenFileName(None, "Choose file", "", self.filt)
            paths = [p] if p else []
        if paths:
            self.paths = paths
            self.status.setText(
                paths[0].split("/")[-1] if len(paths) == 1 else f"{len(paths)} files selected"
            )


class UploadDialog(QDialog):
    """mode='create' collects everything for a new game;
    mode='edit' edits name/description and lets you ADD more media."""

    def __init__(self, parent=None, mode: str = "create", app: dict | None = None):
        super().__init__(parent)
        self.mode = mode
        self.setWindowTitle("Upload game" if mode == "create" else "Edit game")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(10)

        heading = QLabel("Upload a new game" if mode == "create" else "Edit your game")
        heading.setObjectName("SectionLabel")
        layout.addWidget(heading)

        layout.addWidget(QLabel("Name"))
        self.name = QLineEdit()
        if app:
            self.name.setText(app.get("name", ""))
        layout.addWidget(self.name)

        layout.addWidget(QLabel("Description"))
        self.description = QTextEdit()
        self.description.setFixedHeight(90)
        if app:
            self.description.setPlainText(app.get("description", ""))
        layout.addWidget(self.description)

        # Create-only: the game zip + icon
        self.zip_picker = None
        self.icon_picker = None
        if mode == "create":
            layout.addWidget(QLabel("Game file (.zip) — required"))
            self.zip_picker = _FilePicker("Choose .zip", "Zip archives (*.zip)")
            layout.addLayout(self.zip_picker)

            layout.addWidget(QLabel("Icon image (optional)"))
            self.icon_picker = _FilePicker("Choose image", "Images (*.png *.jpg *.jpeg *.ico *.bmp)")
            layout.addLayout(self.icon_picker)

        media_label = "Screenshots" if mode == "create" else "Add screenshots"
        layout.addWidget(QLabel(f"{media_label} (optional)"))
        self.images_picker = _FilePicker("Choose images", "Images (*.png *.jpg *.jpeg *.bmp)", multi=True)
        layout.addLayout(self.images_picker)

        video_label = "Videos" if mode == "create" else "Add videos"
        layout.addWidget(QLabel(f"{video_label} (optional)"))
        self.videos_picker = _FilePicker("Choose videos", "Videos (*.mp4 *.mov *.webm *.avi *.mkv)", multi=True)
        layout.addLayout(self.videos_picker)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Upload" if mode == "create" else "Save changes")
        ok.setObjectName("Primary")
        ok.clicked.connect(self._accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

    def _accept(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, "Missing name", "Please enter a name.")
            return
        if self.mode == "create" and not self.zip_picker.paths:
            QMessageBox.warning(self, "Missing file", "Please choose a .zip game file.")
            return
        self.accept()

    def values(self) -> dict:
        return {
            "name": self.name.text().strip(),
            "description": self.description.toPlainText(),
            "zip": self.zip_picker.paths[0] if (self.zip_picker and self.zip_picker.paths) else None,
            "icon": self.icon_picker.paths[0] if (self.icon_picker and self.icon_picker.paths) else None,
            "images": self.images_picker.paths,
            "videos": self.videos_picker.paths,
        }
