"""
BigEye Pro — Credit History Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget
)
from PySide6.QtCore import Qt
from utils.helpers import format_number


class HistoryDialog(QDialog):
    def __init__(self, transactions: list = None, balance: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ประวัติเครดิต")
        self.setFixedWidth(520)
        self.setMinimumHeight(400)
        self.setStyleSheet("background: #1A1A2E; color: #E8E8E8;")
        self._setup_ui(transactions or [], balance)

    def _setup_ui(self, transactions, balance):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("\U0001F4DC ประวัติเครดิต")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #E8E8E8;")
        layout.addWidget(title)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["วันที่", "รายการ", "จำนวน"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(False)

        # Populate
        self.table.setRowCount(len(transactions))
        for row, tx in enumerate(transactions):
            date_item = QTableWidgetItem(tx.get("date", ""))
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, date_item)

            desc = tx.get("description", "")
            # Add bonus tag for promo top-ups
            if "bonus" in desc.lower():
                desc = "\U0001F381 " + desc
            desc_item = QTableWidgetItem(desc)
            self.table.setItem(row, 1, desc_item)

            amount = tx.get("amount", 0)
            amount_text = f"+{format_number(amount)}" if amount > 0 else format_number(amount)
            amount_item = QTableWidgetItem(amount_text)
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if amount > 0:
                amount_item.setForeground(Qt.GlobalColor.green)
            else:
                amount_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 2, amount_item)

        layout.addWidget(self.table, 1)

        # Balance bar
        bal_widget = QWidget()
        bal_widget.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0, "
            "stop:0 #16213E, stop:1 #0F3460); "
            "border-radius: 8px; padding: 10px;"
        )
        bl = QHBoxLayout(bal_widget)
        bl.setContentsMargins(12, 4, 12, 4)
        blbl = QLabel("ยอดคงเหลือ:")
        blbl.setStyleSheet("color: #8892A8; font-size: 13px;")
        bl.addWidget(blbl)
        bl.addStretch()
        bval = QLabel(f"{format_number(balance)} เครดิต")
        bval.setStyleSheet("color: #FFD700; font-size: 14px; font-weight: 700;")
        bl.addWidget(bval)
        layout.addWidget(bal_widget)

        # Close
        btn = QPushButton("ปิด")
        btn.setMinimumHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
