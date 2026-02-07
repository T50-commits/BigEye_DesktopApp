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
        self.setWindowTitle("Processing Complete")
        self.setFixedWidth(440)
        self.setStyleSheet("background: #1A1A2E; color: #E8E8E8;")
        self._setup_ui(successful, failed, photo_count, video_count,
                       charged, refunded, balance, csv_files)

    def _setup_ui(self, successful, failed, photo_count, video_count,
                  charged, refunded, balance, csv_files):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("\u2705 Processing Complete")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #00E396;")
        layout.addWidget(title)

        # Results card
        results = self._card("RESULTS")
        rl = results.layout()
        self._add_row(rl, "Successful", f"{successful} files", "#00E396")
        if failed > 0:
            self._add_row(rl, "Failed", f"{failed} file{'s' if failed != 1 else ''}", "#FF4560")
        self._add_row(rl, "Breakdown", f"\U0001F4F8 {photo_count} photos \u00B7 \U0001F3AC {video_count} vid", "#8892A8")
        layout.addWidget(results)

        # Credits card
        credits = self._card("CREDITS")
        cl = credits.layout()
        self._add_row(cl, "Charged", f"{format_number(charged)} cr", "#E8E8E8")
        if refunded > 0:
            self._add_row(cl, "Refunded", f"+{format_number(refunded)} cr", "#00E396")
        net = charged - refunded
        self._add_row(cl, "Net cost", f"{format_number(net)} cr", "#E8E8E8")

        sep = QLabel("")
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #1A3A6B;")
        cl.addWidget(sep)

        bal_row = QLabel(f"Balance        {format_number(balance)} credits")
        bal_row.setStyleSheet("color: #FFD700; font-size: 13px; font-weight: 700;")
        cl.addWidget(bal_row)
        layout.addWidget(credits)

        # CSV files card
        if csv_files:
            csv_card = self._card("CSV FILES")
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
            "\U0001F4A1 Remember to review all metadata before uploading. "
            "AI results may need manual adjustments for best rates."
        )
        note.setStyleSheet("color: #8892A8; font-size: 11px;")
        note.setWordWrap(True)
        rl2.addWidget(note)
        layout.addWidget(reminder)

        # Close button
        btn = QPushButton("Close")
        btn.setMinimumHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _card(self, title_text):
        card = QWidget()
        card.setStyleSheet(
            "background: #16213E; border: 1px solid #1A3A6B; "
            "border-radius: 10px; padding: 14px;"
        )
        vl = QVBoxLayout(card)
        vl.setSpacing(6)
        t = QLabel(title_text)
        t.setStyleSheet("color: #8892A8; font-size: 10px; font-weight: 600; letter-spacing: 1.2px;")
        vl.addWidget(t)
        return card

    def _add_row(self, layout, label, value, color):
        from PySide6.QtWidgets import QHBoxLayout
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #8892A8; font-size: 12px;")
        val = QLabel(value)
        val.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
        val.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val)
        layout.addLayout(row)
