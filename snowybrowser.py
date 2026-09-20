#!/usr/bin/env python3
import sys
import os
import shutil
import base64
from urllib.parse import urlparse

from cryptography.fernet import Fernet

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QDialog, QLineEdit, QMessageBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile
from PyQt5.QtCore import QUrl


START_WIDTH = 1300
START_HEIGHT = 850
DEFAULT_ZOOM = 1.0
ALLOWED_DOMAIN = "just-dice.com"

MASTER_FILE_NAME = "master.enc"


# ================= RESOURCE PATH (PyInstaller Safe) =================
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ================= ENCRYPTION =================
def derive_key(password: str):
    return base64.urlsafe_b64encode(password.ljust(32)[:32].encode())


def encrypt_bytes(data: bytes, fernet):
    return fernet.encrypt(data)


def decrypt_bytes(data: bytes, fernet):
    return fernet.decrypt(data)


# ================= PASSWORD DIALOG =================
class PasswordDialog(QDialog):
    def __init__(self, title="Enter Password", confirm=False):
        super().__init__()
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(300, 120)

        layout = QVBoxLayout(self)

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Password")
        layout.addWidget(self.password)

        self.confirm_password = None
        if confirm:
            self.confirm_password = QLineEdit()
            self.confirm_password.setEchoMode(QLineEdit.Password)
            self.confirm_password.setPlaceholderText("Confirm Password")
            layout.addWidget(self.confirm_password)

        btn = QPushButton("OK")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def get_password(self):
        if self.confirm_password:
            if self.password.text() != self.confirm_password.text():
                return None
        return self.password.text()


# ================= DOMAIN LOCK + CONSOLE =================
class LockedPage(QWebEnginePage):
    def __init__(self, profile, parent=None, console_callback=None):
        super().__init__(profile, parent)
        self.console_callback = console_callback

    def acceptNavigationRequest(self, url, nav_type, isMainFrame):
        if not isMainFrame:
            return True

        host = urlparse(url.toString()).hostname
        if not host:
            return False

        return host == ALLOWED_DOMAIN or host.endswith("." + ALLOWED_DOMAIN)

    def createWindow(self, _type):
        return None

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        if self.console_callback:
            self.console_callback(message)


# ================= BROWSER =================
class Browser(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SnowyBot Browser")
        self.resize(START_WIDTH, START_HEIGHT)

        self.app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.base_path = os.path.join(self.app_dir, "portable_data")
        self.profile_path = os.path.join(self.base_path, "profile")
        self.cache_path = os.path.join(self.base_path, "cache")
        self.master_file = os.path.join(self.base_path, MASTER_FILE_NAME)
        self.profile_enc = os.path.join(self.base_path, "profile.enc")

        os.makedirs(self.base_path, exist_ok=True)

        # 🔐 MASTER PASSWORD
        self.master_password = self.load_or_create_master_password()
        self.fernet = Fernet(derive_key(self.master_password))

        self.decrypt_profile()
        os.makedirs(self.profile_path, exist_ok=True)
        os.makedirs(self.cache_path, exist_ok=True)

        self.profile = QWebEngineProfile("PortableProfile", self)
        self.profile.setPersistentStoragePath(self.profile_path)
        self.profile.setCachePath(self.cache_path)
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.ForcePersistentCookies
        )

        self.snowybot_injected = False

        self.init_ui()
        self.new_tab()

    # ================= MASTER PASSWORD =================
    def load_or_create_master_password(self):
        if not os.path.exists(self.master_file):
            dlg = PasswordDialog("Create Master Password", confirm=True)
            if dlg.exec_() != QDialog.Accepted:
                sys.exit()

            password = dlg.get_password()
            if not password:
                QMessageBox.critical(self, "Error", "Passwords do not match.")
                sys.exit()

            fernet = Fernet(derive_key(password))
            encrypted = fernet.encrypt(password.encode())

            with open(self.master_file, "wb") as f:
                f.write(encrypted)

            return password

        else:
            dlg = PasswordDialog("Enter Master Password")
            if dlg.exec_() != QDialog.Accepted:
                sys.exit()

            password = dlg.get_password()
            if not password:
                sys.exit()

            with open(self.master_file, "rb") as f:
                encrypted = f.read()

            fernet = Fernet(derive_key(password))
            try:
                decrypted = fernet.decrypt(encrypted).decode()
                return decrypted
            except Exception:
                QMessageBox.critical(self, "Error", "Incorrect password.")
                sys.exit()

    # ================= UI =================
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        top_bar = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh Page")
        self.refresh_btn.clicked.connect(self.refresh_page)

        self.bot_button = QPushButton("Run SnowyBot")
        self.bot_button.clicked.connect(self.inject_snowybot)

        top_bar.addWidget(self.refresh_btn)
        top_bar.addWidget(self.bot_button)
        top_bar.addStretch()

        layout.addLayout(top_bar)

        self.view = QWebEngineView()
        layout.addWidget(self.view, 8)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet(
            "background-color:black;color:lime;font-family:monospace;"
        )
        layout.addWidget(self.console, 2)

    # ================= TAB =================
    def new_tab(self):
        page = LockedPage(
            self.profile,
            self.view,
            console_callback=self.add_console_line
        )

        self.view.setPage(page)
        self.view.setUrl(QUrl("https://www.just-dice.com"))
        self.view.setZoomFactor(DEFAULT_ZOOM)
        self.view.loadStarted.connect(self.reset_injection_state)

    # ================= CONSOLE =================
    def add_console_line(self, message):
        self.console.append(message)
        self.console.verticalScrollBar().setValue(
            self.console.verticalScrollBar().maximum()
        )

    # ================= SNOWYBOT =================
    def inject_snowybot(self):
        if self.snowybot_injected:
            return

        script_path = resource_path("snowybot.js")
        if not os.path.exists(script_path):
            self.console.append("snowybot.js not found.")
            return

        with open(script_path, "r", encoding="utf-8") as f:
            js_code = f.read()

        self.view.page().runJavaScript(js_code)

        self.snowybot_injected = True
        self.bot_button.setEnabled(False)
        self.console.append("SnowyBot injected.")

    def refresh_page(self):
        self.view.reload()

    def reset_injection_state(self):
        self.snowybot_injected = False
        self.bot_button.setEnabled(True)
        self.console.clear()

    # ================= PROFILE ENCRYPTION =================
    def encrypt_profile(self):
        if not os.path.exists(self.profile_path):
            return

        temp_zip = os.path.join(self.base_path, "temp_profile.zip")
        shutil.make_archive(temp_zip.replace(".zip", ""), "zip", self.profile_path)

        with open(temp_zip, "rb") as f:
            data = f.read()

        encrypted = encrypt_bytes(data, self.fernet)

        with open(self.profile_enc, "wb") as f:
            f.write(encrypted)

        os.remove(temp_zip)
        shutil.rmtree(self.profile_path)

    def decrypt_profile(self):
        if not os.path.exists(self.profile_enc):
            return

        with open(self.profile_enc, "rb") as f:
            encrypted = f.read()

        decrypted = decrypt_bytes(encrypted, self.fernet)

        temp_zip = os.path.join(self.base_path, "temp_profile.zip")
        with open(temp_zip, "wb") as f:
            f.write(decrypted)

        shutil.unpack_archive(temp_zip, self.profile_path, "zip")
        os.remove(temp_zip)
        os.remove(self.profile_enc)


# ================= RUN =================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    browser = Browser()
    browser.show()
    exit_code = app.exec_()
    browser.encrypt_profile()
    sys.exit(exit_code)