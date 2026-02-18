"""
BigEye Pro — Confirm Processing Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QGridLayout
)
from PySide6.QtCore import Qt
from utils.helpers import format_number


class ConfirmDialog(QDialog):
    def __init__(self, file_count: int, photo_count: int, video_count: int,
                 model: str, platform: str, cost: int, balance: int, parent=None,
                 photo_rate: int = 0, video_rate: int = 0):
        super().__init__(parent)
        self.setWindowTitle("ยืนยันการประมวลผล")
        self.setFixedWidth(400)
        self.setStyleSheet("background: #1A1A2E; color: #E8E8E8;")
        self._setup_ui(file_count, photo_count, video_count, model, platform,
                       cost, balance, photo_rate, video_rate)

    def _setup_ui(self, file_count, photo_count, video_count, model, platform,
                  cost, balance, photo_rate, video_rate):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("ยืนยันการประมวลผล")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #E8E8E8;")
        layout.addWidget(title)

        # Info card
        info_card = QWidget()
        info_card.setStyleSheet(
            "background: #16213E; border: 1px solid #1A3A6B; border-radius: 10px; padding: 12px;"
        )
        info_grid = QGridLayout(info_card)
        info_grid.setSpacing(8)

        items = [
            ("ไฟล์", f"{file_count} (ภาพ {photo_count}, วิดีโอ {video_count})"),
            ("โมเดล", model),
            ("แพลตฟอร์ม", platform),
        ]
        for row, (label, value) in enumerate(items):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #8892A8; font-size: 12px;")
            val = QLabel(value)
            val.setStyleSheet("color: #E8E8E8; font-size: 12px; font-weight: 600;")
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            info_grid.addWidget(lbl, row, 0)
            info_grid.addWidget(val, row, 1)

        layout.addWidget(info_card)

        # Cost card
        cost_card = QWidget()
        cost_card.setStyleSheet(
            "background: #16213E; border: 1px solid #1A3A6B; border-radius: 10px; padding: 12px;"
        )
        cost_grid = QGridLayout(cost_card)
        cost_grid.setSpacing(8)

        cost_lbl = QLabel("ค่าใช้จ่าย")
        cost_lbl.setStyleSheet("color: #8892A8; font-size: 12px;")
        cost_text = f"{format_number(cost)} เครดิต"
        if photo_rate and video_rate and photo_rate != video_rate:
            cost_text += f"  (\U0001F4F7 {photo_count}\u00D7{photo_rate} + \U0001F3AC {video_count}\u00D7{video_rate})"
        cost_val = QLabel(cost_text)
        cost_val.setStyleSheet("color: #FFD700; font-size: 12px; font-weight: 700;")
        cost_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        cost_grid.addWidget(cost_lbl, 0, 0)
        cost_grid.addWidget(cost_val, 0, 1)

        after_lbl = QLabel("หลังหักเครดิต")
        after_lbl.setStyleSheet("color: #8892A8; font-size: 12px;")
        after_val = QLabel(f"{format_number(balance - cost)} เครดิต")
        after_val.setStyleSheet("color: #E8E8E8; font-size: 12px; font-weight: 600;")
        after_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        cost_grid.addWidget(after_lbl, 1, 0)
        cost_grid.addWidget(after_val, 1, 1)

        layout.addWidget(cost_card)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_start = QPushButton("Start")
        btn_start.setObjectName("confirmButton")
        btn_start.setMinimumHeight(40)
        btn_start.setMinimumWidth(100)
        btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_start.setStyleSheet("""
            QPushButton#confirmButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FF00CC, stop:1 #7B2FFF);
                border: none;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                padding: 8px 20px;
            }
            QPushButton#confirmButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FF33D6, stop:1 #9B5FFF);
            }
            QPushButton#confirmButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #CC00A3, stop:1 #6222CC);
            }
        """)
        btn_start.clicked.connect(self.accept)
        btn_row.addWidget(btn_start)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setMinimumHeight(40)
        btn_cancel.setMinimumWidth(100)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        layout.addLayout(btn_row)
