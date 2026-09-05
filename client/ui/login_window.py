"""Login / register screen."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QHBoxLayout,
    QFrame,
)
from PySide6.QtCore import Qt

from api import ApiClient, ApiError


class LoginWindow(QWidget):
    def __init__(self, api: ApiClient, on_success):
        super().__init__()
        self.api = api
        self.on_success = on_success  # callback(username) after successful login

        self.setWindowTitle("Epic Store — Sign in")
        self.setFixedSize(420, 420)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 30, 30, 30)

        # Centered card
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(14)
        layout.setContentsMargins(28, 28, 28, 28)

        title = QLabel("Epic Store")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Sign in to browse and download apps")
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        layout.addWidget(self.username)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.returnPressed.connect(self.handle_login)
        layout.addWidget(self.password)
        layout.addSpacing(6)

        login_btn = QPushButton("Log in")
        login_btn.setObjectName("Primary")
        login_btn.clicked.connect(self.handle_login)
        layout.addWidget(login_btn)

        register_btn = QPushButton("Create an account")
        register_btn.clicked.connect(self.handle_register)
        layout.addWidget(register_btn)

        layout.addStretch()
        outer.addStretch()
        outer.addWidget(card)
        outer.addStretch()

    def handle_login(self):
        try:
            self.api.login(self.username.text().strip(), self.password.text())
        except ApiError as e:
            QMessageBox.warning(self, "Login failed", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Connection error", f"Could not reach server:\n{e}")
            return
        self.on_success(self.username.text().strip())

    def handle_register(self):
        try:
            self.api.register(self.username.text().strip(), self.password.text())
        except ApiError as e:
            QMessageBox.warning(self, "Register failed", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Connection error", f"Could not reach server:\n{e}")
            return
        QMessageBox.information(self, "Success", "Account created! You can log in now.")
