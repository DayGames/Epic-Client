"""Login / register screen."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QHBoxLayout,
)
from PySide6.QtCore import Qt

from api import ApiClient, ApiError


class LoginWindow(QWidget):
    def __init__(self, api: ApiClient, on_success):
        super().__init__()
        self.api = api
        self.on_success = on_success  # callback(username) after successful login

        self.setWindowTitle("Epic Client — Sign in")
        self.setFixedSize(360, 300)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Epic Client")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        layout.addWidget(self.username)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.returnPressed.connect(self.handle_login)
        layout.addWidget(self.password)

        buttons = QHBoxLayout()
        login_btn = QPushButton("Log in")
        login_btn.clicked.connect(self.handle_login)
        register_btn = QPushButton("Register")
        register_btn.clicked.connect(self.handle_register)
        buttons.addWidget(login_btn)
        buttons.addWidget(register_btn)
        layout.addLayout(buttons)

        layout.addStretch()

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
