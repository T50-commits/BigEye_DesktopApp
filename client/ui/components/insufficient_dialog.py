"""
BigEye Pro — Insufficient Credit Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
)
from PySide6.QtCore import Qt, Signal
from utils.helpers import format_number


class InsufficientDialog(QDialog):
    topup_requested = Signal()
    partial_requested = Signal(int)  # max affordable file count

    def __init__(self, required: int, available: int, rate: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("เครดิตไม่เพียงพอ")
        self.setFixedWidth(420)
        self.setStyleSheet("background: #1A1A2E; color: #E8E8E8;")
        self._max_files = available // rate
        self._setup_ui(required, available, rate)

    def _setup_ui(self, required, available, rate):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("\u26A0\uFE0F เครดิตไม่เพียงพอ")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #FEB019;")
        layout.addWidget(title)

        # Info
        info = QWidget()
        info.setStyleSheet(
            "background: #16213E; border: 1px solid #1A3A6B; border-radius: 10px; padding: 14px;"
        )
        il = QVBoxLayout(info)
        il.setSpacing(6)

        for label, value, color in [
            ("ต้องการ:", f"{format_number(required)} เครดิต", "#E8E8E8"),
            ("คงเหลือ:", f"{format_number(available)} เครดิต", "#E8E8E8"),
            ("ขาดอีก:", f"{format_number(required - available)} เครดิต", "#FF4560"),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #8892A8; font-size: 12px;")
            val = QLabel(value)
            val.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            il.addLayout(row)

        layout.addWidget(info)

        # Buttons
        btn_topup = QPushButton("เติมเครดิต")
        btn_topup.setObjectName("confirmButton")
        btn_topup.setMinimumHeight(40)
        btn_topup.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_topup.clicked.connect(self._on_topup)
        layout.addWidget(btn_topup)

        if self._max_files > 0:
            btn_partial = QPushButton(f"ประมวลผลบางส่วน {self._max_files} ไฟล์")
            btn_partial.setMinimumHeight(40)
            btn_partial.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_partial.clicked.connect(self._on_partial)
            layout.addWidget(btn_partial)

        btn_cancel = QPushButton("ยกเลิก")
        btn_cancel.setMinimumHeight(40)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel)

    def _on_topup(self):
        self.topup_requested.emit()
        self.reject()

    def _on_partial(self):
        self.partial_requested.emit(self._max_files)
        self.accept()
