"""
BigEye Pro — Top-Up Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QLineEdit, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent


class DropZone(QFrame):
    """Drag-and-drop zone for payment slip."""
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self.setStyleSheet(
            "border: 2px dashed #264773; border-radius: 12px; "
            "background: #16213E; color: #8892A8; font-size: 12px;"
        )
        self._filepath = ""

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label = QLabel("\U0001F4CE Drop payment slip here\nor click to browse")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #8892A8; font-size: 12px; border: none;")
        layout.addWidget(self.label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(
                "border: 2px dashed #FF00CC; border-radius: 12px; "
                "background: #FF00CC10; color: #FF00CC; font-size: 12px;"
            )

    def dragLeaveEvent(self, event):
        self.setStyleSheet(
            "border: 2px dashed #264773; border-radius: 12px; "
            "background: #16213E; color: #8892A8; font-size: 12px;"
        )

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self._filepath = path
            self.label.setText(f"\u2705 {path.split('/')[-1]}")
            self.label.setStyleSheet("color: #00E396; font-size: 12px; border: none;")
            self.file_dropped.emit(path)
        self.setStyleSheet(
            "border: 2px dashed #264773; border-radius: 12px; "
            "background: #16213E; color: #8892A8; font-size: 12px;"
        )

    def mousePressEvent(self, event):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Payment Slip", "",
            "Images (*.png *.jpg *.jpeg *.pdf)"
        )
        if path:
            self._filepath = path
            self.label.setText(f"\u2705 {path.split('/')[-1]}")
            self.label.setStyleSheet("color: #00E396; font-size: 12px; border: none;")
            self.file_dropped.emit(path)

    def get_filepath(self) -> str:
        return self._filepath


class TopUpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Top Up Credits")
        self.setFixedWidth(460)
        self.setStyleSheet("background: #1A1A2E; color: #E8E8E8;")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("\U0001FA99 Top Up Credits")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #E8E8E8;")
        layout.addWidget(title)

        # Bank info card
        bank = QWidget()
        bank.setStyleSheet(
            "background: #16213E; border: 1px solid #1A3A6B; "
            "border-radius: 10px; padding: 14px;"
        )
        bl = QVBoxLayout(bank)
        bl.setSpacing(6)

        bt = QLabel("TRANSFER TO")
        bt.setStyleSheet("color: #8892A8; font-size: 10px; font-weight: 600; letter-spacing: 1.2px;")
        bl.addWidget(bt)

        bl.addWidget(self._info_label("\U0001F3E6 Kasikornbank xxx-x-xxxxx-x"))
        bl.addWidget(self._info_label("Account: XXXXX XXXXX"))

        rate = QLabel("Rate: 1 THB = 4 Credits")
        rate.setStyleSheet("color: #FFD700; font-size: 12px; font-weight: 600;")
        bl.addWidget(rate)

        layout.addWidget(bank)

        # Drop zone
        self.drop_zone = DropZone()
        layout.addWidget(self.drop_zone)

        # Amount
        amt_row = QHBoxLayout()
        amt_label = QLabel("Amount:")
        amt_label.setStyleSheet("color: #8892A8; font-size: 12px;")
        amt_row.addWidget(amt_label)

        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("0")
        self.amount_input.setFixedWidth(120)
        self.amount_input.setMinimumHeight(36)
        amt_row.addWidget(self.amount_input)

        thb = QLabel("THB")
        thb.setStyleSheet("color: #8892A8; font-size: 12px;")
        amt_row.addWidget(thb)
        amt_row.addStretch()
        layout.addLayout(amt_row)

        # Submit
        self.btn_submit = QPushButton("Submit Slip")
        self.btn_submit.setObjectName("confirmButton")
        self.btn_submit.setMinimumHeight(42)
        self.btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit.clicked.connect(self._on_submit)
        layout.addWidget(self.btn_submit)

        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #8892A8; font-size: 12px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # Close
        btn_close = QPushButton("Close")
        btn_close.setMinimumHeight(38)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)

    def _info_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #E8E8E8; font-size: 12px;")
        return lbl

    def _on_submit(self):
        slip = self.drop_zone.get_filepath()
        amount = self.amount_input.text().strip()
        if not slip:
            self.status_label.setText("\u274C Please attach a payment slip")
            self.status_label.setStyleSheet("color: #FF4560; font-size: 12px;")
            return
        if not amount or not amount.isdigit():
            self.status_label.setText("\u274C Please enter a valid amount")
            self.status_label.setStyleSheet("color: #FF4560; font-size: 12px;")
            return
        self.status_label.setText("\u23F3 Verifying...")
        self.status_label.setStyleSheet("color: #FEB019; font-size: 12px;")
        # TODO: Implement actual API call
