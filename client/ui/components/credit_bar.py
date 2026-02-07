"""
BigEye Pro — Top Bar / Credit Bar Component
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import (
    QFont, QLinearGradient, QColor, QPainter, QBrush, QPen
)

from core.config import (
    TOP_BAR_HEIGHT, CREDIT_REFRESH_INTERVAL, LOW_CREDIT_THRESHOLD
)
from utils.helpers import format_number


class GradientLogoLabel(QLabel):
    """BIGEYE logo with gradient text."""

    def __init__(self, parent=None):
        super().__init__("BIGEYE", parent)
        font = QFont("Helvetica Neue", 14)
        font.setWeight(QFont.Weight.ExtraBold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        self.setFont(font)
        self.setFixedHeight(TOP_BAR_HEIGHT)
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0.0, QColor("#FF00CC"))
        gradient.setColorAt(1.0, QColor("#7B2FFF"))

        pen = QPen(QBrush(gradient), 1)
        painter.setPen(pen)
        painter.setFont(self.font())
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.text()
        )
        painter.end()


class CreditBar(QWidget):
    """Top bar with logo, credit balance, and user actions."""

    topup_clicked = Signal()
    refresh_clicked = Signal()
    history_clicked = Signal()
    logout_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(TOP_BAR_HEIGHT)
        self.setStyleSheet(f"""
            QWidget#creditBarWidget {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #16213E, stop:1 #1A1A2E);
                border-bottom: 1px solid #1A3A6B;
            }}
        """)
        self.setObjectName("creditBarWidget")

        self._balance = 0
        self._user_name = ""
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        # Logo
        logo = GradientLogoLabel()
        logo.setFixedWidth(80)
        layout.addWidget(logo)

        # Vertical divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFixedHeight(20)
        divider.setStyleSheet("color: #1A3A6B;")
        layout.addWidget(divider)

        # Credit icon + amount
        self.credit_icon = QLabel("\U0001F4B0")
        self.credit_icon.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.credit_icon)

        self.credit_label = QLabel("0")
        self.credit_label.setObjectName("creditLabel")
        layout.addWidget(self.credit_label)

        credits_text = QLabel("credits")
        credits_text.setStyleSheet("color: #4A5568; font-size: 11px;")
        layout.addWidget(credits_text)

        # Top Up chip
        self.btn_topup = QPushButton("Top Up")
        self.btn_topup.setObjectName("topUpChip")
        self.btn_topup.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_topup.clicked.connect(self.topup_clicked.emit)
        layout.addWidget(self.btn_topup)

        # Refresh chip
        self.btn_refresh = QPushButton("\u21BB")
        self.btn_refresh.setObjectName("chipButton")
        self.btn_refresh.setToolTip("Refresh Balance")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_clicked.emit)
        layout.addWidget(self.btn_refresh)

        # History chip
        self.btn_history = QPushButton("History")
        self.btn_history.setObjectName("chipButton")
        self.btn_history.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_history.clicked.connect(self.history_clicked.emit)
        layout.addWidget(self.btn_history)

        # Spacer
        layout.addStretch(1)

        # User name
        self.user_label = QLabel("")
        self.user_label.setStyleSheet("color: #8892A8; font-size: 12px;")
        layout.addWidget(self.user_label)

        # Logout chip
        self.btn_logout = QPushButton("Logout")
        self.btn_logout.setObjectName("chipButton")
        self.btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_logout.clicked.connect(self.logout_clicked.emit)
        layout.addWidget(self.btn_logout)

    def _setup_timer(self):
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_clicked.emit)
        self._refresh_timer.start(CREDIT_REFRESH_INTERVAL)

    def set_balance(self, balance: int):
        """Update the credit balance display."""
        self._balance = balance
        self.credit_label.setText(format_number(balance))
        if balance < LOW_CREDIT_THRESHOLD:
            self.credit_label.setObjectName("creditLabelLow")
        else:
            self.credit_label.setObjectName("creditLabel")
        self.credit_label.style().unpolish(self.credit_label)
        self.credit_label.style().polish(self.credit_label)

    def set_user_name(self, name: str):
        """Update the displayed user name."""
        self._user_name = name
        self.user_label.setText(name)

    def set_processing(self, is_processing: bool):
        """Lock/unlock controls during processing."""
        self.btn_refresh.setEnabled(not is_processing)
        self.btn_logout.setEnabled(not is_processing)

    def get_balance(self) -> int:
        return self._balance
