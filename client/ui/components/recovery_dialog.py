"""
BigEye Pro — Recovery Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QWidget
)
from PySide6.QtCore import Qt
from utils.helpers import format_number


class RecoveryDialog(QDialog):
    def __init__(self, info: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Unfinished Job Found")
        self.setFixedWidth(400)
        self.setStyleSheet("background: #1A1A2E; color: #E8E8E8;")
        self._info = info or {}
        self._setup_ui()

    def _setup_ui(self):
        info = self._info
        platform = info.get("platform", "Unknown")
        total_files = info.get("total_files", 0)
        completed = info.get("completed", 0)
        ok_count = info.get("ok_count", 0)
        failed_count = info.get("failed_count", 0)
        credits_reserved = info.get("credits_reserved", 0)
        refunded = info.get("refunded", 0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("\u26A0\uFE0F Unfinished Job Found")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #FEB019;")
        layout.addWidget(title)

        # Info card
        card = QWidget()
        card.setStyleSheet(
            "background: #16213E; border: 1px solid #1A3A6B; "
            "border-radius: 10px; padding: 14px;"
        )
        cl = QVBoxLayout(card)
        cl.setSpacing(6)

        info_items = [
            f"Job: {platform}, {total_files} files",
            f"Completed: {completed} ({ok_count} ok, {failed_count} failed)",
            f"Credits reserved: {format_number(credits_reserved)}",
        ]
        for text in info_items:
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #E8E8E8; font-size: 12px;")
            cl.addWidget(lbl)

        # Refund info
        if refunded > 0:
            refund_lbl = QLabel(f"Refunded: +{format_number(refunded)} credits")
            refund_lbl.setStyleSheet("color: #00E396; font-size: 12px; font-weight: 600;")
            cl.addWidget(refund_lbl)

        layout.addWidget(card)

        btn = QPushButton("OK")
        btn.setObjectName("confirmButton")
        btn.setMinimumHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
