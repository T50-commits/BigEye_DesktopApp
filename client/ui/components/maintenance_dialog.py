"""
BigEye Pro — Maintenance Dialog
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt


class MaintenanceDialog(QDialog):
    def __init__(self, parent=None, message: str = "", force_close: bool = True):
        super().__init__(parent)
        self.setWindowTitle("ปิดปรับปรุงระบบ")
        self.setFixedWidth(360)
        self.setStyleSheet("background: #1A1A2E; color: #E8E8E8;")
        self._force_close = force_close
        self._setup_ui(message)

    def _setup_ui(self, message: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("\U0001F527 ปิดปรับปรุงระบบชั่วคราว")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #FEB019;")
        layout.addWidget(title)

        display_msg = message or "ระบบปิดปรับปรุงชั่วคราว กรุณาลองใหม่ภายหลัง"
        msg = QLabel(display_msg)
        msg.setStyleSheet("color: #8892A8; font-size: 13px;")
        msg.setWordWrap(True)
        layout.addWidget(msg)

        btn = QPushButton("ตกลง")
        btn.setMinimumHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def accept(self):
        super().accept()
        if self._force_close and self.parent():
            self.parent().close()
