"""Login / register screen (borderless)."""
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QMessageBox
from PySide6.QtCore import Qt

from api import ApiClient, ApiError
from ui.frameless import FramelessWindow


class LoginWindow(FramelessWindow):
    def __init__(self, api: ApiClient, on_success):
        super().__init__("Epic Store")
        self.api = api
        self.on_success = on_success  # callback(username) after successful login
        self.setFixedSize(420, 440)

        self.body.setContentsMargins(34, 10, 34, 30)
        self.body.setSpacing(14)

        self.body.addStretch()

        title = QLabel("Epic Store")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        self.body.addWidget(title)

        subtitle = QLabel("Sign in to browse and download apps")
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        self.body.addWidget(subtitle)
        self.body.addSpacing(10)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.body.addWidget(self.username)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.returnPressed.connect(self.handle_login)
        self.body.addWidget(self.password)
        self.body.addSpacing(6)

        login_btn = QPushButton("Log in")
        login_btn.setObjectName("Primary")
        login_btn.clicked.connect(self.handle_login)
        self.body.addWidget(login_btn)

        register_btn = QPushButton("Create an account")
        register_btn.clicked.connect(self.handle_register)
        self.body.addWidget(register_btn)

        self.body.addStretch()

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
