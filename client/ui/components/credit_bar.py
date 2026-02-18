"""
BigEye Pro — Top Bar / Credit Bar Component
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame,
    QSizePolicy
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
        self.setObjectName("creditBarWidget")
        self._balance = 0
        self._user_name = ""
        self._active_promos = []
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Promo Banner (hidden by default) ──
        self.promo_banner = QWidget()
        self.promo_banner.setObjectName("promoBanner")
        self.promo_banner.hide()
        banner_layout = QHBoxLayout(self.promo_banner)
        banner_layout.setContentsMargins(16, 8, 16, 8)
        banner_layout.setSpacing(12)

        self.promo_text = QLabel("")
        self.promo_text.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        banner_layout.addWidget(self.promo_text, 1)

        btn_topup_now = QPushButton("เติมเงินเลย")
        btn_topup_now.setObjectName("bannerTopUp")
        btn_topup_now.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_topup_now.setStyleSheet("""
            QPushButton#bannerTopUp {
                background: #00E396;
                border: 1px solid #00C07B;
                border-radius: 10px;
                padding: 4px 14px;
                color: #000000;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton#bannerTopUp:hover {
                background: #00FF9F;
            }
        """)
        btn_topup_now.clicked.connect(self.topup_clicked.emit)
        banner_layout.addWidget(btn_topup_now)

        btn_close_banner = QPushButton("\u2715")
        btn_close_banner.setObjectName("bannerClose")
        btn_close_banner.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close_banner.setFixedSize(22, 22)
        btn_close_banner.setStyleSheet("""
            QPushButton#bannerClose {
                background: transparent;
                border: none;
                color: #FFFFFFAA;
                font-size: 14px;
            }
            QPushButton#bannerClose:hover { color: #FFFFFF; }
        """)
        btn_close_banner.clicked.connect(self.hide_banner)
        banner_layout.addWidget(btn_close_banner)

        outer.addWidget(self.promo_banner)

        # ── Credit Bar Row ──
        credit_row = QWidget()
        credit_row.setFixedHeight(TOP_BAR_HEIGHT)
        credit_row.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #16213E, stop:1 #1A1A2E);
                border-bottom: 1px solid #1A3A6B;
            }
        """)
        layout = QHBoxLayout(credit_row)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # Logo
        logo = GradientLogoLabel()
        logo.setFixedWidth(100)
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

        credits_text = QLabel("เครดิต")
        credits_text.setStyleSheet("color: #4A5568; font-size: 11px;")
        layout.addWidget(credits_text)

        # Top Up chip
        self.btn_topup = QPushButton("เติมเงิน")
        self.btn_topup.setObjectName("topUpChip")
        self.btn_topup.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_topup.setStyleSheet("""
            QPushButton#topUpChip {
                background: #FFD70015;
                border: 1px solid #FFD70033;
                border-radius: 12px;
                padding: 4px 14px;
                color: #FFD700;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#topUpChip:hover {
                background: #FFD70025;
                border-color: #FFD70066;
            }
        """)
        self.btn_topup.clicked.connect(self.topup_clicked.emit)
        layout.addWidget(self.btn_topup)

        # Refresh chip
        self.btn_refresh = self._make_chip("\u21BB", "รีเฟรชยอด")
        self.btn_refresh.clicked.connect(self.refresh_clicked.emit)
        layout.addWidget(self.btn_refresh)

        # History chip
        self.btn_history = self._make_chip("ประวัติ")
        self.btn_history.clicked.connect(self.history_clicked.emit)
        layout.addWidget(self.btn_history)

        # Spacer
        layout.addStretch(1)

        # User name
        self.user_label = QLabel("")
        self.user_label.setStyleSheet("color: #8892A8; font-size: 12px;")
        layout.addWidget(self.user_label)

        # Logout chip
        self.btn_logout = self._make_chip("ออกจากระบบ")
        self.btn_logout.clicked.connect(self.logout_clicked.emit)
        layout.addWidget(self.btn_logout)

        outer.addWidget(credit_row)

    def _make_chip(self, text: str, tooltip: str = "") -> QPushButton:
        """Create a styled chip button."""
        btn = QPushButton(text)
        btn.setObjectName("chipButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            btn.setToolTip(tooltip)
        btn.setStyleSheet("""
            QPushButton#chipButton {
                background: transparent;
                border: 1px solid #1A3A6B;
                border-radius: 12px;
                padding: 4px 12px;
                color: #8892A8;
                font-size: 11px;
            }
            QPushButton#chipButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FF00CC18, stop:1 #7B2FFF18);
                border-color: #FF00CC66;
                color: #FF00CC;
            }
        """)
        return btn

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

    def set_promos(self, promos: list):
        """Show promo banner if there are active promotions."""
        self._active_promos = promos or []
        if not self._active_promos:
            self.promo_banner.hide()
            return

        # Show the highest priority promo's banner
        best = self._active_promos[0]
        banner_text = best.get("banner_text", "")
        banner_color = best.get("banner_color", "#FF4560")

        if not banner_text:
            self.promo_banner.hide()
            return

        self.promo_text.setText(banner_text)
        self.promo_banner.setStyleSheet(f"""
            QWidget#promoBanner {{
                background: {banner_color};
                border-bottom: 1px solid {banner_color};
            }}
        """)
        self.promo_banner.show()

    def hide_banner(self):
        """Hide the promo banner (user dismissed)."""
        self.promo_banner.hide()

    def get_active_promos(self) -> list:
        return self._active_promos
