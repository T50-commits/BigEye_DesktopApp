# BigEye Pro — UI Fix: ComboBox Dropdown + Re-export CSV
### Copy ทั้งหมดไปสั่ง AI IDE

---

## Fix 1: QComboBox Dropdown ไม่มี hover highlight

### ไฟล์: `client/ui/components/sidebar.py`

### วิธีแก้: เพิ่ม COMBO_STYLE constant แล้ว apply ให้ทุก ComboBox

**เพิ่มที่บรรทัดบนสุด (หลัง import):**

```python
COMBO_STYLE = """
    QComboBox {
        background: #16213E;
        border: 1px solid #1A3A6B;
        border-radius: 8px;
        padding: 10px 12px;
        color: #E8E8E8;
        font-size: 13px;
    }
    QComboBox:hover {
        border-color: #264773;
    }
    QComboBox:focus {
        border-color: #FF00CC;
    }
    QComboBox::drop-down {
        border: none;
        width: 30px;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #8892A8;
        margin-right: 10px;
    }
    QComboBox QAbstractItemView {
        background: #16213E;
        border: 1px solid #1A3A6B;
        border-radius: 6px;
        padding: 4px;
        outline: none;
        selection-background-color: transparent;
    }
    QComboBox QAbstractItemView::item {
        background: transparent;
        color: #8892A8;
        padding: 8px 12px;
        border-radius: 4px;
        min-height: 20px;
    }
    QComboBox QAbstractItemView::item:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #FF00CC18, stop:1 #7B2FFF18);
        color: #FF00CC;
    }
    QComboBox QAbstractItemView::item:selected {
        background: #FF00CC22;
        color: #FF00CC;
    }
"""
```

**แก้ทุกจุดที่สร้าง QComboBox (3 จุด):**

จุดที่ 1 — Model combo (ประมาณบรรทัด 163):
```python
# ❌ เดิม:
self.combo_model = QComboBox()
self.combo_model.addItems(AI_MODELS)
self.combo_model.setMinimumHeight(38)

# ✅ เพิ่ม 1 บรรทัด:
self.combo_model = QComboBox()
self.combo_model.addItems(AI_MODELS)
self.combo_model.setMinimumHeight(38)
self.combo_model.setStyleSheet(COMBO_STYLE)       # ← เพิ่ม
```

จุดที่ 2 — Platform combo (ประมาณบรรทัด 173):
```python
self.combo_platform = QComboBox()
self.combo_platform.addItems(PLATFORMS)
self.combo_platform.setMinimumHeight(38)
self.combo_platform.setStyleSheet(COMBO_STYLE)     # ← เพิ่ม
```

จุดที่ 3 — Keyword Style combo (ประมาณบรรทัด 183):
```python
self.combo_keyword_style = QComboBox()
self.combo_keyword_style.addItems(KEYWORD_STYLES)
self.combo_keyword_style.setMinimumHeight(38)
self.combo_keyword_style.setStyleSheet(COMBO_STYLE) # ← เพิ่ม
```

**รวม: แก้ไข 1 ไฟล์ เพิ่ม 1 constant + เพิ่ม 3 บรรทัด `.setStyleSheet(COMBO_STYLE)`**

---

## Fix 2: Title 1 บรรทัด → 2 บรรทัด

### ไฟล์: `client/ui/components/inspector.py`

**บรรทัด 172-176 — เปลี่ยน QLineEdit → QTextEdit:**

```python
# ❌ เดิม:
el.addWidget(self._make_label("Title"))
self.title_edit = QLineEdit()
self.title_edit.setMinimumHeight(36)
self.title_edit.editingFinished.connect(self._on_edit)
el.addWidget(self.title_edit)

# ✅ ใหม่:
el.addWidget(self._make_label("Title"))
self.title_edit = QTextEdit()
self.title_edit.setFixedHeight(56)
self.title_edit.setAcceptRichText(False)
self.title_edit.setTabChangesFocus(True)
self.title_edit.setStyleSheet("QTextEdit { font-size: 12px; padding: 6px 8px; }")
el.addWidget(self.title_edit)
```

**บรรทัด ~213 ใน _on_edit() — เปลี่ยน .text() → .toPlainText():**

```python
# ❌ เดิม:
"title": self.title_edit.text(),

# ✅ ใหม่:
"title": self.title_edit.toPlainText().replace("\n", " ").strip(),
```

**บรรทัด ~240 ใน show_file() — เปลี่ยน setText → setPlainText:**

```python
# ❌ เดิม:
self.title_edit.setText(result.get("title", ""))

# ✅ ใหม่:
self.title_edit.setPlainText(result.get("title", ""))
```

---

## Fix 3: Export CSV → Re-export CSV

### ไฟล์: `client/ui/components/inspector.py`

**บรรทัด 193 — เปลี่ยนข้อความปุ่ม:**

```python
# ❌ เดิม:
self.btn_export = QPushButton("\U0001F4BE Export CSV")

# ✅ ใหม่:
self.btn_export = QPushButton("🔄 Re-export CSV")
```

**เพิ่ม style ให้ปุ่ม (บรรทัด 194-197):**

```python
# ❌ เดิม:
self.btn_export.setObjectName("exportButton")
self.btn_export.setMinimumHeight(38)
self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
self.btn_export.clicked.connect(self.export_clicked.emit)

# ✅ ใหม่:
self.btn_export.setObjectName("exportButton")
self.btn_export.setMinimumHeight(38)
self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
self.btn_export.setEnabled(False)  # disabled จนกว่าจะมี completed files
self.btn_export.setStyleSheet("""
    QPushButton#exportButton {
        background: #00B4D812;
        border: 1px solid #00B4D833;
        border-radius: 8px;
        padding: 7px 14px;
        color: #00B4D8;
        font-size: 12px;
        font-weight: 500;
    }
    QPushButton#exportButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #FF00CC18, stop:1 #7B2FFF18);
        border-color: #FF00CC66;
        color: #FF00CC;
    }
    QPushButton#exportButton:disabled {
        color: #4A5568;
        border-color: #1A3A6B44;
        background: transparent;
    }
""")
self.btn_export.clicked.connect(self.export_clicked.emit)
```

**เพิ่ม method enable_export() เพื่อเปิดปุ่มหลัง auto-save เสร็จ:**

```python
def enable_export(self, enabled: bool = True):
    """Enable Re-export button after job completes and auto-save is done."""
    self.btn_export.setEnabled(enabled)
```

**ใน main_window.py หรือ job_manager.py — เรียก enable หลัง job เสร็จ:**

```python
# หลัง auto-save CSV สำเร็จ:
self.inspector.enable_export(True)

# เมื่อเปิด folder ใหม่ หรือเริ่ม job ใหม่:
self.inspector.enable_export(False)
```

---

## Fix 4: export_csv_dialog.py — เปลี่ยนเป็น Re-export

### ไฟล์: `client/ui/components/export_csv_dialog.py`

**เปลี่ยน title ของ dialog:**

```python
# ❌ เดิม:
self.setWindowTitle("Export CSV")
# หรือ title label ที่แสดง "💾 Export CSV"

# ✅ ใหม่:
self.setWindowTitle("Re-export CSV")
# title label: "🔄 Re-export CSV"
```

**เพิ่มกล่อง info สีฟ้าเหนือ warning (ถ้ายังไม่มี):**

```python
# Info box (ใหม่ — เพิ่มก่อน warning box)
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

info_icon = QLabel("ℹ️")
info_icon.setStyleSheet("font-size: 22px; background: transparent; border: none;")
info_layout.addWidget(info_icon, 0)

info_text = QLabel(
    "<b style='color: #00B4D8;'>Re-export with Your Edits</b><br>"
    "<span style='color: #8892A8; font-size: 12px;'>"
    "This will generate new CSV files that include any changes "
    "you've made to titles, descriptions, and keywords.</span>"
)
info_text.setWordWrap(True)
info_text.setStyleSheet("background: transparent; border: none;")
info_layout.addWidget(info_text, 1)

# เพิ่มใน layout ก่อน warning box
layout.addWidget(info_box)
```

**เปลี่ยนข้อความปุ่ม confirm:**

```python
# ❌ เดิม:
self.btn_confirm = QPushButton("Export CSV")

# ✅ ใหม่:
self.btn_confirm = QPushButton("Re-export CSV")
```

---

## สรุปทุกไฟล์ที่ต้องแก้

| ไฟล์ | แก้อะไร |
|:--|:--|
| `sidebar.py` | เพิ่ม COMBO_STYLE + apply ให้ 3 ComboBox |
| `inspector.py` | Title → QTextEdit 2 บรรทัด + ปุ่ม Re-export + disabled by default |
| `export_csv_dialog.py` | เปลี่ยน title + เพิ่ม info box + ปุ่ม Re-export |
| `main_window.py` (หรือ `job_manager.py`) | เรียก `inspector.enable_export(True)` หลัง auto-save |

ทั้งหมดเป็นการแก้ UI ไม่กระทบ business logic
