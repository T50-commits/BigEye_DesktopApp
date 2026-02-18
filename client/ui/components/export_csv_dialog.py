"""
BigEye Pro — Export CSV Dialog (with warning + checklist)
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QCheckBox
)
from PySide6.QtCore import Qt, Signal


class ExportCsvDialog(QDialog):
    export_confirmed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Re-export CSV")
        self.setFixedWidth(440)
        self.setStyleSheet("background: #1A1A2E; color: #E8E8E8;")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("\U0001F504 Re-export CSV")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #E8E8E8;")
        layout.addWidget(title)

        # Info box
        info_box = QWidget()
        info_box.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #00B4D812, stop:1 #00B4D806);
                border: 1px solid #00B4D833;
                border-radius: 12px;
            }
        """)
        info_layout = QHBoxLayout(info_box)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(12)

        info_icon = QLabel("\u2139\uFE0F")
        info_icon.setStyleSheet("font-size: 22px; background: transparent; border: none;")
        info_layout.addWidget(info_icon, 0)

        info_text = QLabel(
            "<b style='color: #00B4D8;'>ส่งออก CSV ใหม่พร้อมการแก้ไขของคุณ</b><br>"
            "<span style='color: #8892A8; font-size: 12px;'>"
            "ระบบจะสร้างไฟล์ CSV ใหม่ที่รวมการแก้ไข "
            "ชื่อเรื่อง, คำอธิบาย และคีย์เวิร์ดที่คุณปรับแล้ว</span>"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("background: transparent; border: none;")
        info_layout.addWidget(info_text, 1)

        layout.addWidget(info_box)

        # Warning box
        warning = QWidget()
        warning.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, "
            "stop:0 #FEB01912, stop:1 #FEB01906); "
            "border: 1px solid #FEB01933; border-radius: 12px; padding: 16px;"
        )
        wl = QVBoxLayout(warning)
        wl.setSpacing(8)

        warn_title = QLabel("\u26A0\uFE0F กรุณาตรวจสอบก่อนอัปโหลด")
        warn_title.setStyleSheet("color: #FEB019; font-size: 13px; font-weight: 700;")
        wl.addWidget(warn_title)

        warn_body = QLabel(
            "ข้อมูลที่สร้างโดย AI อาจมีข้อผิดพลาดหรือไม่ถูกต้อง "
            "เราแนะนำให้ตรวจสอบชื่อเรื่อง คำอธิบาย และคีย์เวิร์ดทั้งหมด "
            "ก่อนส่งไปยังแพลตฟอร์มขายภาพ เพื่อเพิ่มอัตราการอนุมัติ "
            "และลดโอกาสถูกปฏิเสธ"
        )
        warn_body.setStyleSheet("color: #8892A8; font-size: 12px; line-height: 1.6;")
        warn_body.setWordWrap(True)
        wl.addWidget(warn_body)

        layout.addWidget(warning)

        # Checklist
        checklist = QWidget()
        checklist.setStyleSheet(
            "background: #16213E; border: 1px solid #1A3A6B; "
            "border-radius: 10px; padding: 14px;"
        )
        cl = QVBoxLayout(checklist)
        cl.setSpacing(8)

        cl_title = QLabel("รายการตรวจสอบ")
        cl_title.setStyleSheet(
            "color: #8892A8; font-size: 10px; font-weight: 600; letter-spacing: 1.2px;"
        )
        cl.addWidget(cl_title)

        checks = [
            "ชื่อเรื่องตรงกับเนื้อหาในภาพ/วิดีโอ",
            "คำอธิบายมีรายละเอียดครบถ้วน",
            "คีย์เวิร์ดไม่มีคำที่เป็นเครื่องหมายการค้า",
        ]
        self.checkboxes = []
        for text in checks:
            cb = QCheckBox(text)
            cb.setStyleSheet(
                "QCheckBox { color: #E8E8E8; font-size: 12px; spacing: 8px; }"
                "QCheckBox::indicator { width: 16px; height: 16px; "
                "border: 1px solid #1A3A6B; border-radius: 3px; background: #16213E; }"
                "QCheckBox::indicator:checked { background: #FF00CC; border-color: #FF00CC; }"
            )
            self.checkboxes.append(cb)
            cl.addWidget(cb)

        layout.addWidget(checklist)

        # Buttons
        btn_row = QHBoxLayout()

        btn_export = QPushButton("Re-export CSV")
        btn_export.setObjectName("confirmButton")
        btn_export.setMinimumHeight(42)
        btn_export.setMinimumWidth(130)
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.clicked.connect(self._on_export)
        btn_row.addWidget(btn_export)

        btn_row.addSpacing(12)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setMinimumHeight(42)
        btn_cancel.setMinimumWidth(100)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _on_export(self):
        self.export_confirmed.emit()
        self.accept()
