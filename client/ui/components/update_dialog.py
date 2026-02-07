"""
BigEye Pro — Update Dialog (Optional / Force)
"""
import webbrowser
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt


class UpdateDialog(QDialog):
    def __init__(self, version: str = "", download_url: str = "",
                 force: bool = False, parent=None, notes: str = ""):
        super().__init__(parent)
        self._download_url = download_url
        self._force = force

        if force:
            self.setWindowTitle("Update Required")
            self.setWindowFlags(
                self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
            )
        else:
            self.setWindowTitle("Update Available")

        self.setFixedWidth(360)
        self.setStyleSheet("background: #1A1A2E; color: #E8E8E8;")
        self._setup_ui(version, notes, force)

    def _setup_ui(self, version, notes, force):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        if force:
            icon_text = "\u26A0\uFE0F Update Required"
            icon_color = "#FEB019"
        else:
            icon_text = "\U0001F195 Update Available"
            icon_color = "#00B4D8"

        title = QLabel(icon_text)
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {icon_color};")
        layout.addWidget(title)

        ver = QLabel(f"Version: {version}")
        ver.setStyleSheet("color: #E8E8E8; font-size: 13px;")
        layout.addWidget(ver)

        if notes:
            note = QLabel(f'"{notes}"')
            note.setStyleSheet("color: #8892A8; font-size: 12px; font-style: italic;")
            note.setWordWrap(True)
            layout.addWidget(note)

        btn_row = QHBoxLayout()

        if force:
            btn_dl = QPushButton("Download Update")
            btn_dl.setObjectName("confirmButton")
        else:
            btn_dl = QPushButton("Update Now")
            btn_dl.setObjectName("confirmButton")

        btn_dl.setMinimumHeight(40)
        btn_dl.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dl.clicked.connect(self._on_download)
        btn_row.addWidget(btn_dl)

        if not force:
            btn_skip = QPushButton("Skip")
            btn_skip.setMinimumHeight(40)
            btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_skip.clicked.connect(self.reject)
            btn_row.addWidget(btn_skip)

        layout.addLayout(btn_row)

    def _on_download(self):
        if self._download_url:
            webbrowser.open(self._download_url)
        if self._force:
            import sys
            sys.exit(0)
        else:
            self.accept()

    def closeEvent(self, event):
        if self._force:
            event.ignore()
        else:
            super().closeEvent(event)
