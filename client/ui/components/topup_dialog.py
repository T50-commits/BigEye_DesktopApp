"""
BigEye Pro — Top-Up Dialog
Slip2Go QR-code verification flow:
  1. User drops/selects a payment slip image
  2. OpenCV decodes the QR code from the image
  3. User clicks "Verify & Top Up"
  4. Server verifies QR data with Slip2Go API → credits user automatically
"""
import logging
import threading

import cv2
import numpy as np
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QLineEdit, QFrame, QApplication,
)
from PySide6.QtCore import Qt, Signal, QMetaObject, Q_ARG, Slot
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QImage

from core.api_client import api

logger = logging.getLogger("bigeye-client")

_STYLE_DROP_IDLE = (
    "border: 2px dashed #264773; border-radius: 12px; "
    "background: #16213E; color: #8892A8; font-size: 12px;"
)
_STYLE_DROP_HOVER = (
    "border: 2px dashed #FF00CC; border-radius: 12px; "
    "background: #FF00CC10; color: #FF00CC; font-size: 12px;"
)


def decode_qr_from_image(filepath: str) -> str | None:
    """Read an image file and try to decode a QR code using OpenCV."""
    try:
        img = cv2.imread(filepath)
        if img is None:
            return None
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(img)
        if data:
            return data
        # Retry with grayscale + threshold for low-quality images
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        data, _, _ = detector.detectAndDecode(thresh)
        return data if data else None
    except Exception as e:
        logger.warning(f"QR decode failed: {e}")
        return None


class SlipDropZone(QFrame):
    """Drag-and-drop zone for payment slip image. Decodes QR automatically."""
    qr_decoded = Signal(str)   # emitted with QR data on success
    qr_failed = Signal()       # emitted when no QR found
    file_selected = Signal(str)  # emitted with filepath

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(140)
        self.setStyleSheet(_STYLE_DROP_IDLE)
        self._filepath = ""
        self._qr_data = ""

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        self.icon_label = QLabel("\U0001F4F7")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 28px; border: none; background: transparent;")
        layout.addWidget(self.icon_label)

        self.label = QLabel("ลากรูปสลิปมาวางที่นี่\nหรือคลิกเพื่อเลือกไฟล์")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #8892A8; font-size: 12px; border: none; background: transparent;")
        layout.addWidget(self.label)

        self.qr_status = QLabel("")
        self.qr_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_status.setStyleSheet("font-size: 11px; border: none; background: transparent;")
        self.qr_status.hide()
        layout.addWidget(self.qr_status)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(_STYLE_DROP_HOVER)

    def dragLeaveEvent(self, event):
        self.setStyleSheet(_STYLE_DROP_IDLE)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(_STYLE_DROP_IDLE)
        urls = event.mimeData().urls()
        if urls:
            self._process_file(urls[0].toLocalFile())

    def mousePressEvent(self, event):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "เลือกรูปสลิปการโอน", "",
            "รูปภาพ (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self._process_file(path)

    def _process_file(self, path: str):
        self._filepath = path
        self._qr_data = ""
        filename = path.split("/")[-1].split("\\")[-1]
        self.label.setText(f"\u2705 {filename}")
        self.label.setStyleSheet("color: #00E396; font-size: 12px; border: none; background: transparent;")
        self.qr_status.setText("\u23F3 กำลังสแกน QR code...")
        self.qr_status.setStyleSheet("color: #FEB019; font-size: 11px; border: none; background: transparent;")
        self.qr_status.show()
        self.file_selected.emit(path)

        # Decode QR in background thread to keep UI responsive
        threading.Thread(target=self._decode_qr, args=(path,), daemon=True).start()

    def _decode_qr(self, path: str):
        qr = decode_qr_from_image(path)
        if qr:
            self._qr_data = qr
            QMetaObject.invokeMethod(
                self, "_on_qr_success", Qt.ConnectionType.QueuedConnection,
            )
        else:
            QMetaObject.invokeMethod(
                self, "_on_qr_fail", Qt.ConnectionType.QueuedConnection,
            )

    @Slot()
    def _on_qr_success(self):
        self.qr_status.setText("\u2705 พบ QR Code แล้ว")
        self.qr_status.setStyleSheet("color: #00E396; font-size: 11px; border: none; background: transparent;")
        self.icon_label.setText("\u2705")
        self.setStyleSheet(
            "border: 2px solid #00E396; border-radius: 12px; "
            "background: #16213E; color: #00E396; font-size: 12px;"
        )
        self.qr_decoded.emit(self._qr_data)

    @Slot()
    def _on_qr_fail(self):
        self.qr_status.setText("\u274C ไม่พบ QR Code — ลองใช้รูปที่ชัดกว่านี้")
        self.qr_status.setStyleSheet("color: #FF4560; font-size: 11px; border: none; background: transparent;")
        self.icon_label.setText("\u274C")
        self.setStyleSheet(
            "border: 2px solid #FF4560; border-radius: 12px; "
            "background: #16213E; color: #FF4560; font-size: 12px;"
        )
        self.qr_failed.emit()

    def get_qr_data(self) -> str:
        return self._qr_data

    def get_filepath(self) -> str:
        return self._filepath


class TopUpDialog(QDialog):
    def __init__(self, parent=None, promos: list = None, bank_info: dict = None):
        super().__init__(parent)
        self.setWindowTitle("เติมเครดิต")
        self.setFixedWidth(760)
        self.setStyleSheet("background: #1A1A2E; color: #E8E8E8;")
        self._promos = promos or []
        self._bank_info = bank_info or {}
        self._qr_ready = False
        self._submitting = False
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ── Title ──
        title = QLabel("\U0001FA99 เติมเครดิต")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #E8E8E8;")
        root.addWidget(title)

        # ── 2-column body ──
        body = QHBoxLayout()
        body.setSpacing(16)

        # ════════════════════════════
        # LEFT COLUMN — info
        # ════════════════════════════
        left = QVBoxLayout()
        left.setSpacing(12)

        # Steps card
        steps = QWidget()
        steps.setStyleSheet(
            "background: #16213E; border: 1px solid #1A3A6B; "
            "border-radius: 10px; padding: 14px;"
        )
        sl = QVBoxLayout(steps)
        sl.setSpacing(5)
        how_title = QLabel("ขั้นตอนการเติมเงิน")
        how_title.setStyleSheet(
            "color: #8892A8; font-size: 10px; font-weight: 600; "
            "letter-spacing: 1.2px; border: none;"
        )
        sl.addWidget(how_title)
        for num, text in [
            ("1", "โอนเงินไปยังบัญชีธนาคารด้านขวา"),
            ("2", "แคปหน้าจอสลิปการโอน"),
            ("3", "ลากรูปสลิปมาวางในกล่องด้านขวา"),
            ("4", "กด 'ตรวจสอบและเติมเงิน' — เครดิตเข้าทันที"),
        ]:
            row = QHBoxLayout()
            n = QLabel(num)
            n.setFixedWidth(18)
            n.setStyleSheet("color: #FFD700; font-size: 11px; font-weight: 700; border: none;")
            t = QLabel(text)
            t.setStyleSheet("color: #C8C8D8; font-size: 11px; border: none;")
            row.addWidget(n)
            row.addWidget(t)
            row.addStretch()
            sl.addLayout(row)
        left.addWidget(steps)

        # Bank info card
        bank = QWidget()
        bank.setStyleSheet(
            "background: #16213E; border: 1px solid #1A3A6B; "
            "border-radius: 10px; padding: 14px;"
        )
        bl = QVBoxLayout(bank)
        bl.setSpacing(7)
        bt = QLabel("โอนเงินไปที่")
        bt.setStyleSheet(
            "color: #8892A8; font-size: 10px; font-weight: 600; letter-spacing: 1.2px; border: none;"
        )
        bl.addWidget(bt)
        bank_name = self._bank_info.get("bank_name") or "ยังไม่ได้ตั้งค่า"
        account_number = self._bank_info.get("account_number") or "—"
        account_name = self._bank_info.get("account_name") or "—"
        bl.addWidget(self._info_label(f"\U0001F3E6 {bank_name}  {account_number}"))
        bl.addWidget(self._info_label(f"ชื่อบัญชี: {account_name}"))
        rate_lbl = QLabel("อัตรา: 1 บาท = 4 เครดิต")
        rate_lbl.setStyleSheet("color: #FFD700; font-size: 12px; font-weight: 600; border: none;")
        bl.addWidget(rate_lbl)
        left.addWidget(bank)

        # Promo display (optional)
        if self._promos:
            best = self._promos[0]
            color = best.get("banner_color", "#FF4560")
            promo_box = QWidget()
            promo_box.setObjectName("promoBox")
            promo_box.setStyleSheet(f"""
                QWidget#promoBox {{
                    background: {color}18;
                    border: 1px solid {color}44;
                    border-radius: 10px;
                }}
            """)
            pl = QVBoxLayout(promo_box)
            pl.setContentsMargins(14, 10, 14, 10)
            pl.setSpacing(5)
            promo_title = QLabel(best.get("banner_text", best.get("name", "")))
            promo_title.setWordWrap(True)
            promo_title.setStyleSheet(
                f"color: {color}; font-size: 12px; font-weight: 700; "
                "background: transparent; border: none;"
            )
            pl.addWidget(promo_title)
            tiers = best.get("tiers")
            if tiers:
                for t in tiers:
                    min_b = int(t.get("min_baht", 0))
                    cr = int(t.get("credits", 0))
                    star = " \u2B50" if cr > min_b * 4 else ""
                    tl = QLabel(f"  เติม {min_b} บาท \u2192 {cr:,} เครดิต{star}")
                    tl.setStyleSheet("color: #E8E8E8; font-size: 11px; background: transparent; border: none;")
                    pl.addWidget(tl)
            override = best.get("override_rate")
            if override:
                ol = QLabel(f"  อัตราพิเศษ: 1 บาท = {int(override)} เครดิต")
                ol.setStyleSheet("color: #E8E8E8; font-size: 11px; background: transparent; border: none;")
                pl.addWidget(ol)
            ends = best.get("ends_at", "")
            if ends:
                el = QLabel(f"  สิ้นสุด: {ends[:10]}")
                el.setStyleSheet("color: #8892A8; font-size: 10px; background: transparent; border: none;")
                pl.addWidget(el)
            left.addWidget(promo_box)

        left.addStretch()
        body.addLayout(left, stretch=1)

        # ════════════════════════════
        # RIGHT COLUMN — action
        # ════════════════════════════
        right = QVBoxLayout()
        right.setSpacing(12)

        # Drop zone
        self.drop_zone = SlipDropZone()
        self.drop_zone.setMinimumHeight(160)
        self.drop_zone.qr_decoded.connect(self._on_qr_decoded)
        self.drop_zone.qr_failed.connect(self._on_qr_failed)
        right.addWidget(self.drop_zone)

        # Promo code input
        code_row = QHBoxLayout()
        code_label = QLabel("รหัสโปรโมชั่น:")
        code_label.setStyleSheet("color: #8892A8; font-size: 12px;")
        code_row.addWidget(code_label)
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("ไม่บังคับ")
        self.code_input.setMinimumHeight(36)
        code_row.addWidget(self.code_input, stretch=1)
        right.addLayout(code_row)

        # Submit button
        self.btn_submit = QPushButton("\U0001F50D ตรวจสอบและเติมเงิน")
        self.btn_submit.setObjectName("confirmButton")
        self.btn_submit.setMinimumHeight(44)
        self.btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit.setEnabled(False)
        self.btn_submit.clicked.connect(self._on_submit)
        right.addWidget(self.btn_submit)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #8892A8; font-size: 12px;")
        self.status_label.setWordWrap(True)
        right.addWidget(self.status_label)

        # Result card (hidden until success)
        self.result_card = QWidget()
        self.result_card.setObjectName("resultCard")
        self.result_card.setStyleSheet("""
            QWidget#resultCard {
                background: #00E39618;
                border: 1px solid #00E39644;
                border-radius: 10px;
            }
        """)
        self.result_card.hide()
        rl = QVBoxLayout(self.result_card)
        rl.setContentsMargins(14, 12, 14, 12)
        rl.setSpacing(4)
        self.result_title = QLabel("")
        self.result_title.setStyleSheet(
            "color: #00E396; font-size: 14px; font-weight: 700; "
            "border: none; background: transparent;"
        )
        rl.addWidget(self.result_title)
        self.result_detail = QLabel("")
        self.result_detail.setWordWrap(True)
        self.result_detail.setStyleSheet(
            "color: #C8C8D8; font-size: 12px; border: none; background: transparent;"
        )
        rl.addWidget(self.result_detail)
        right.addWidget(self.result_card)

        right.addStretch()
        body.addLayout(right, stretch=1)

        root.addLayout(body)

        # ── Close button ──
        btn_close = QPushButton("ปิด")
        btn_close.setMinimumHeight(36)
        btn_close.setFixedWidth(100)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        root.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

    # ── Helpers ──

    def _info_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #E8E8E8; font-size: 12px;")
        return lbl

    def _on_qr_decoded(self, qr_data: str):
        self._qr_ready = True
        self.btn_submit.setEnabled(True)
        self.status_label.setText("")

    def _on_qr_failed(self):
        self._qr_ready = False
        self.btn_submit.setEnabled(False)
        self.status_label.setText(
            "\u274C ไม่สามารถอ่าน QR code จากรูปได้\n"
            "กรุณาใช้รูปสลิปที่ชัดเจนกว่านี้"
        )
        self.status_label.setStyleSheet("color: #FF4560; font-size: 12px;")

    def _on_submit(self):
        if self._submitting:
            return
        qr_data = self.drop_zone.get_qr_data()
        if not qr_data:
            self.status_label.setText("\u274C ไม่มีข้อมูล QR code — กรุณาแนบสลิปก่อน")
            self.status_label.setStyleSheet("color: #FF4560; font-size: 12px;")
            return

        self._submitting = True
        self.btn_submit.setEnabled(False)
        self.btn_submit.setText("\u23F3 กำลังตรวจสอบกับธนาคาร...")
        self.status_label.setText("\u23F3 กำลังส่งข้อมูลไป Slip2Go เพื่อตรวจสอบ...")
        self.status_label.setStyleSheet("color: #FEB019; font-size: 12px;")
        self.result_card.hide()
        QApplication.processEvents()

        promo_code = self.code_input.text().strip()

        # Run API call in background thread
        threading.Thread(
            target=self._do_topup, args=(qr_data, promo_code), daemon=True
        ).start()

    def _do_topup(self, qr_data: str, promo_code: str):
        try:
            result = api.topup(qr_data, promo_code)
            QMetaObject.invokeMethod(
                self, "_on_topup_success", Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, str(result.get("total_credits", 0))),
                Q_ARG(str, str(result.get("base_credits", 0))),
                Q_ARG(str, str(result.get("bonus_credits", 0))),
                Q_ARG(str, str(result.get("new_balance", 0))),
                Q_ARG(str, result.get("promo_applied", "") or ""),
                Q_ARG(str, result.get("message", "")),
            )
        except Exception as e:
            msg = str(e)
            # Try to extract detail from APIError
            if hasattr(e, "detail"):
                msg = e.detail
            QMetaObject.invokeMethod(
                self, "_on_topup_error", Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, msg),
            )

    @Slot(str, str, str, str, str, str)
    def _on_topup_success(self, total: str, base: str, bonus: str,
                          new_balance: str, promo: str, message: str):
        self._submitting = False
        self.btn_submit.setText("\u2705 สำเร็จ!")
        self.status_label.setText("")

        detail_parts = [f"เครดิตพื้นฐาน: +{int(base):,} เครดิต"]
        if int(bonus) > 0:
            detail_parts.append(f"โบนัส: +{int(bonus):,} เครดิต")
        if promo:
            detail_parts.append(f"โปรโมชั่น: {promo}")
        detail_parts.append(f"ยอดคงเหลือ: {int(new_balance):,} เครดิต")

        self.result_title.setText(f"\u2705 เติมสำเร็จ +{int(total):,} เครดิต!")
        self.result_detail.setText("\n".join(detail_parts))
        self.result_card.show()

        # Refresh parent's balance
        parent = self.parent()
        if parent and hasattr(parent, "_on_refresh_balance"):
            parent._on_refresh_balance()

    @Slot(str)
    def _on_topup_error(self, error_msg: str):
        self._submitting = False
        self.btn_submit.setEnabled(True)
        self.btn_submit.setText("\U0001F50D ตรวจสอบและเติมเงิน")
        self.status_label.setText(f"\u274C {error_msg}")
        self.status_label.setStyleSheet("color: #FF4560; font-size: 12px;")
