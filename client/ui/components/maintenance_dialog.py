"""
BigEye Pro — Maintenance Dialog
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt


class MaintenanceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Server Maintenance")
        self.setFixedWidth(360)
        self.setStyleSheet("background: #1A1A2E; color: #E8E8E8;")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("\U0001F527 Server Maintenance")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #FEB019;")
        layout.addWidget(title)

        msg = QLabel(
            "The server is temporarily unavailable for maintenance. "
            "Please try again later."
        )
        msg.setStyleSheet("color: #8892A8; font-size: 13px;")
        msg.setWordWrap(True)
        layout.addWidget(msg)

        btn = QPushButton("OK")
        btn.setMinimumHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
