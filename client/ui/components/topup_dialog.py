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
    def __init__(self, parent=None, promos: list = None):
        super().__init__(parent)
        self.setWindowTitle("Top Up Credits")
        self.setFixedWidth(460)
        self.setStyleSheet("background: #1A1A2E; color: #E8E8E8;")
        self._promos = promos or []
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

        # Promo display (if active promos exist)
        if self._promos:
            best = self._promos[0]
            promo_box = QWidget()
            promo_box.setObjectName("promoBox")
            color = best.get("banner_color", "#FF4560")
            promo_box.setStyleSheet(f"""
                QWidget#promoBox {{
                    background: {color}18;
                    border: 1px solid {color}44;
                    border-radius: 10px;
                }}
            """)
            pl = QVBoxLayout(promo_box)
            pl.setContentsMargins(14, 10, 14, 10)
            pl.setSpacing(6)

            promo_title = QLabel(best.get("banner_text", best.get("name", "")))
            promo_title.setWordWrap(True)
            promo_title.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 700; background: transparent; border: none;")
            pl.addWidget(promo_title)

            # Show tiers if available
            tiers = best.get("tiers")
            if tiers:
                for t in tiers:
                    min_b = int(t.get("min_baht", 0))
                    cr = int(t.get("credits", 0))
                    base = min_b * 4
                    star = " \u2B50" if cr > base else ""
                    tier_lbl = QLabel(f"  Top up {min_b} THB \u2192 {cr:,} credits{star}")
                    tier_lbl.setStyleSheet("color: #E8E8E8; font-size: 11px; background: transparent; border: none;")
                    pl.addWidget(tier_lbl)

            # Show rate override
            override = best.get("override_rate")
            if override:
                rate_lbl = QLabel(f"  Special rate: 1 THB = {int(override)} credits")
                rate_lbl.setStyleSheet("color: #E8E8E8; font-size: 11px; background: transparent; border: none;")
                pl.addWidget(rate_lbl)

            ends = best.get("ends_at", "")
            if ends:
                end_short = ends[:10] if len(ends) > 10 else ends
                end_lbl = QLabel(f"  Ends: {end_short}")
                end_lbl.setStyleSheet("color: #8892A8; font-size: 10px; background: transparent; border: none;")
                pl.addWidget(end_lbl)

            layout.addWidget(promo_box)

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

        # Credit preview
        self.preview_label = QLabel("")
        self.preview_label.setStyleSheet("color: #00E396; font-size: 12px; font-weight: 600;")
        self.preview_label.hide()
        layout.addWidget(self.preview_label)
        self.amount_input.textChanged.connect(self._update_preview)

        # Promo code input
        code_row = QHBoxLayout()
        code_label = QLabel("Promo Code:")
        code_label.setStyleSheet("color: #8892A8; font-size: 12px;")
        code_row.addWidget(code_label)
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Optional")
        self.code_input.setFixedWidth(160)
        self.code_input.setMinimumHeight(36)
        code_row.addWidget(self.code_input)
        code_row.addStretch()
        layout.addLayout(code_row)

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

    def _update_preview(self, text: str):
        """Update credit preview as user types amount."""
        if not text or not text.isdigit() or int(text) <= 0:
            self.preview_label.hide()
            return

        amount = int(text)
        base = amount * 4
        bonus = 0

        # Check if any promo gives bonus
        if self._promos:
            best = self._promos[0]
            tiers = best.get("tiers")
            override = best.get("override_rate")
            pct = best.get("bonus_percentage")
            flat = best.get("bonus_credits")

            if tiers:
                for t in sorted(tiers, key=lambda x: x.get("min_baht", 0), reverse=True):
                    if amount >= t.get("min_baht", 0):
                        bonus = t.get("credits", 0) - base
                        break
            elif override:
                bonus = int(amount * override) - base
            elif pct:
                bonus = int(base * pct / 100)
            elif flat:
                bonus = flat

        total = base + max(bonus, 0)
        if bonus > 0:
            self.preview_label.setText(
                f"You will receive: {total:,} credits ({base:,} base + {bonus:,} bonus \U0001F381)"
            )
        else:
            self.preview_label.setText(f"You will receive: {total:,} credits")
        self.preview_label.show()

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
