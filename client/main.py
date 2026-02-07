"""
BigEye Pro — Main Entry Point (Task B-04)
"""
import sys
import os

# Ensure the client directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from core.config import APP_NAME, get_asset_path
from core.auth_manager import AuthManager
from ui.auth_window import AuthWindow
from ui.main_window import MainWindow
from utils.logger import setup_logger


def load_stylesheet(app: QApplication):
    """Load the QSS dark theme stylesheet."""
    qss_path = get_asset_path(os.path.join("assets", "styles", "dark_theme.qss"))
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        print(f"[WARN] QSS file not found: {qss_path}")


def main():
    logger = setup_logger()
    logger.info(f"Starting {APP_NAME}")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")

    # Load theme
    load_stylesheet(app)

    # Set app icon if available
    icon_path = get_asset_path(os.path.join("assets", "icons", "app_icon.png"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Auth flow — skip for testing
    auth_manager = AuthManager()
    jwt_token = "dev_token"
    user_name = "Developer"

    # To enable auth, uncomment below and remove the 2 lines above:
    # jwt_token = ""
    # user_name = ""
    # if auth_manager.has_valid_token():
    #     jwt_token = "saved"
    #     user_name = auth_manager.user_name or "User"
    #     logger.info(f"Auto-login: {user_name}")
    # else:
    #     auth = AuthWindow(auth_manager=auth_manager)
    #     def on_login(token, name):
    #         nonlocal jwt_token, user_name
    #         jwt_token, user_name = token, name
    #     auth.login_success.connect(on_login)
    #     if auth.exec() != AuthWindow.DialogCode.Accepted:
    #         sys.exit(0)

    # Main window
    window = MainWindow(user_name=user_name, jwt_token=jwt_token, auth_manager=auth_manager)
    window.show()

    logger.info("Application started successfully")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
