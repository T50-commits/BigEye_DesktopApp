"""
BigEye Pro — Job Summary Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QWidget, QGridLayout
)
from PySide6.QtCore import Qt
from utils.helpers import format_number


class SummaryDialog(QDialog):
    def __init__(self, successful: int, failed: int, photo_count: int,
                 video_count: int, charged: int, refunded: int,
                 balance: int, csv_files: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ประมวลผลเสร็จสิ้น")
        self.setFixedWidth(440)
        self.setStyleSheet("background: #1A1A2E; color: #E8E8E8;")
        self._setup_ui(successful, failed, photo_count, video_count,
                       charged, refunded, balance, csv_files)

    def _setup_ui(self, successful, failed, photo_count, video_count,
                  charged, refunded, balance, csv_files):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("\u2705 ประมวลผลเสร็จสิ้น")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #00E396;")
        layout.addWidget(title)

        # Results card
        results = self._card("ผลลัพธ์")
        rl = results.layout()
        self._add_row(rl, "สำเร็จ", f"{successful} ไฟล์", "#00E396")
        if failed > 0:
            self._add_row(rl, "ล้มเหลว", f"{failed} ไฟล์", "#FF4560")
        self._add_row(rl, "รายละเอียด", f"\U0001F4F8 {photo_count} ภาพ \u00B7 \U0001F3AC {video_count} วิดีโอ", "#8892A8")
        layout.addWidget(results)

        # Credits card
        credits = self._card("เครดิต")
        cl = credits.layout()
        self._add_row(cl, "หักไป", f"{format_number(charged)} เครดิต", "#E8E8E8")
        if refunded > 0:
            self._add_row(cl, "คืนเครดิต", f"+{format_number(refunded)} เครดิต", "#00E396")
        net = charged - refunded
        self._add_row(cl, "สุทธิ", f"{format_number(net)} เครดิต", "#E8E8E8")

        sep = QLabel("")
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #1A3A6B;")
        cl.addWidget(sep)

        from PySide6.QtWidgets import QHBoxLayout
        bal_layout = QHBoxLayout()
        bal_layout.setContentsMargins(0, 0, 0, 0)
        bal_lbl = QLabel("ยอดคงเหลือ:")
        bal_lbl.setStyleSheet("color: #FFD700; font-size: 14px; font-weight: 700; border: none; background: transparent;")
        bal_val = QLabel(f"{format_number(balance)} เครดิต")
        bal_val.setStyleSheet("color: #FFD700; font-size: 14px; font-weight: 700; border: none; background: transparent;")
        bal_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        bal_layout.addWidget(bal_lbl)
        bal_layout.addStretch()
        bal_layout.addWidget(bal_val)
        cl.addLayout(bal_layout)
        layout.addWidget(credits)

        # CSV files card
        if csv_files:
            csv_card = self._card("ไฟล์ CSV")
            cvl = csv_card.layout()
            for f in csv_files:
                fl = QLabel(f"\u2705 {f}")
                fl.setStyleSheet("color: #00E396; font-size: 11px;")
                fl.setWordWrap(True)
                cvl.addWidget(fl)
            layout.addWidget(csv_card)

        # Reminder
        reminder = QWidget()
        reminder.setStyleSheet(
            "background: #16213E; border: 1px solid #1A3A6B; "
            "border-radius: 10px; padding: 12px;"
        )
        rl2 = QVBoxLayout(reminder)
        rl2.setContentsMargins(0, 0, 0, 0)
        note = QLabel(
            "\U0001F4A1 กรุณาตรวจสอบข้อมูลทั้งหมดก่อนอัปโหลด "
            "ผลลัพธ์จาก AI อาจต้องปรับแก้เพื่อให้ได้อัตราอนุมัติดีที่สุด"
        )
        note.setStyleSheet("color: #8892A8; font-size: 11px;")
        note.setWordWrap(True)
        rl2.addWidget(note)
        layout.addWidget(reminder)

        # Close button
        btn = QPushButton("ปิด")
        btn.setMinimumHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _card(self, title_text):
        card = QWidget()
        card.setStyleSheet(
            "QWidget { background: #16213E; border: 1px solid #1A3A6B; border-radius: 10px; }"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(14, 14, 14, 14)
        vl.setSpacing(8)
        t = QLabel(title_text)
        t.setStyleSheet("color: #8892A8; font-size: 10px; font-weight: 600; letter-spacing: 1.2px; border: none; background: transparent;")
        vl.addWidget(t)
        return card

    def _add_row(self, layout, label, value, color):
        from PySide6.QtWidgets import QHBoxLayout
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #8892A8; font-size: 13px; border: none; background: transparent;")
        val = QLabel(value)
        val.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 600; border: none; background: transparent;")
        val.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val)
        layout.addLayout(row)
