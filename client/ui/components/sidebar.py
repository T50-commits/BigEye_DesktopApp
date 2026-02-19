"""
BigEye Pro — Left Sidebar Component
"""
import os
import platform
import subprocess

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSlider, QScrollArea, QFrame,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from core.config import (
    SIDEBAR_WIDTH, AI_MODELS, AI_MODEL_INFO, PLATFORMS, KEYWORD_STYLES,
    SLIDER_CONFIGS, DEBUG_LOG_PATH
)

COMBO_BOX_STYLE = """
    QComboBox {
        background: #16213E;
        border: 1px solid #1A3A6B;
        border-radius: 8px;
        padding: 10px 12px;
        color: #E8E8E8;
        font-size: 13px;
    }
    QComboBox:hover {
        border-color: #4f8cff;
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
"""

COMBO_POPUP_STYLE = """
    QFrame {
        background: #16213E;
        border: 1px solid #1A3A6B;
        border-radius: 6px;
    }
"""

COMBO_VIEW_STYLE = """
    QListView {
        background: #16213E;
        border: none;
        padding: 4px;
        outline: none;
        selection-background-color: #3D2066;
        selection-color: #FF00CC;
    }
    QListView::item {
        background: transparent;
        color: #C8D0E0;
        padding: 8px 12px;
        min-height: 20px;
    }
    QListView::item:hover {
        background: #2D3A5E;
        color: #FFFFFF;
        border-radius: 4px;
    }
    QListView::item:selected {
        background: #3D2066;
        color: #FF00CC;
        font-weight: bold;
        border-radius: 4px;
    }
"""


def style_combo(combo: QComboBox):
    """Style a QComboBox including its popup (which is a separate top-level window)."""
    combo.setStyleSheet(COMBO_BOX_STYLE)
    # The popup view is a QListView inside a QFrame that is a TOP-LEVEL window,
    # NOT a child of QComboBox — so CSS descendant selectors don't work.
    # We must style the view and its parent frame directly.
    view = combo.view()
    view.setStyleSheet(COMBO_VIEW_STYLE)
    popup_frame = view.parentWidget()
    if popup_frame:
        popup_frame.setStyleSheet(COMBO_POPUP_STYLE)


class SectionDivider(QWidget):
    """Horizontal line — SECTION TITLE — horizontal line."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(8)

        line_left = QFrame()
        line_left.setFrameShape(QFrame.Shape.HLine)
        line_left.setStyleSheet("color: #1A3A6B;")
        line_left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        label = QLabel(title.upper())
        label.setObjectName("sectionLabel")
        label.setStyleSheet(
            "color: #8892A8; font-size: 10px; font-weight: 500; "
            "letter-spacing: 1.2px;"
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        line_right = QFrame()
        line_right.setFrameShape(QFrame.Shape.HLine)
        line_right.setStyleSheet("color: #1A3A6B;")
        line_right.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout.addWidget(line_left)
        layout.addWidget(label)
        layout.addWidget(line_right)


class SliderRow(QWidget):
    """Label + Slider + Value display, synced."""

    value_changed = Signal(int)

    def __init__(self, label: str, config: dict, parent=None):
        super().__init__(parent)
        self._config = config

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Top row: label + value
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: #8892A8; font-size: 11px;")
        top.addWidget(lbl)

        top.addStretch()

        self.value_label = QLabel(str(config["default"]))
        self.value_label.setStyleSheet(
            "color: #E8E8E8; font-size: 12px; font-weight: 600;"
        )
        self.value_label.setMinimumWidth(30)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        top.addWidget(self.value_label)

        layout.addLayout(top)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(config["min"])
        self.slider.setMaximum(config["max"])
        self.slider.setValue(config["default"])
        self.slider.setSingleStep(config["step"])
        self.slider.setPageStep(config["step"])
        self.slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.slider)

    def _on_value_changed(self, value: int):
        # Snap to step
        step = self._config["step"]
        snapped = round(value / step) * step
        if snapped != value:
            self.slider.blockSignals(True)
            self.slider.setValue(snapped)
            self.slider.blockSignals(False)
            value = snapped
        self.value_label.setText(str(value))
        self.value_changed.emit(value)

    def get_value(self) -> int:
        return self.slider.value()

    def set_value(self, val: int):
        self.slider.setValue(val)


class Sidebar(QWidget):
    """Left sidebar with API Key, AI Settings, Metadata sliders, Debug Log."""

    api_key_saved = Signal(str)
    api_key_cleared = Signal()
    model_changed = Signal(str)
    platform_changed = Signal(str)
    keyword_style_changed = Signal(str)
    keywords_changed = Signal(int)
    title_length_changed = Signal(int)
    description_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setStyleSheet("background: #1A1A2E;")
        self._setup_ui()

    def _setup_ui(self):
        # Scroll area wrapper
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self.layout_main = QVBoxLayout(content)
        self.layout_main.setContentsMargins(16, 14, 16, 14)
        self.layout_main.setSpacing(6)

        # ── API KEY ──
        self.layout_main.addWidget(SectionDivider("API Key"))

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Google Gemini API Key")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setMinimumHeight(38)
        self.layout_main.addWidget(self.api_key_input)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_save_key = QPushButton("\U0001F4BE Save")
        self.btn_save_key.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_key.clicked.connect(self._on_save_key)
        btn_row.addWidget(self.btn_save_key)

        self.btn_clear_key = QPushButton("\U0001F5D1 Clear")
        self.btn_clear_key.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_key.clicked.connect(self._on_clear_key)
        btn_row.addWidget(self.btn_clear_key)

        self.layout_main.addLayout(btn_row)

        # ── AI SETTINGS ──
        self.layout_main.addSpacing(4)
        self.layout_main.addWidget(SectionDivider("AI Settings"))

        # Model
        model_label = QLabel("Model")
        model_label.setStyleSheet("color: #8892A8; font-size: 11px;")
        self.layout_main.addWidget(model_label)

        self.combo_model = QComboBox()
        for model_id in AI_MODELS:
            info = AI_MODEL_INFO.get(model_id, {})
            label = info.get("label", model_id)
            self.combo_model.addItem(label, userData=model_id)
            idx = self.combo_model.count() - 1
            self.combo_model.setItemData(idx, info.get("description", ""), Qt.ItemDataRole.ToolTipRole)
        # Default to gemini-2.5-flash
        default_idx = next(
            (i for i in range(self.combo_model.count())
             if self.combo_model.itemData(i) == "gemini-2.5-flash"), 0
        )
        self.combo_model.setCurrentIndex(default_idx)
        self.combo_model.setMinimumHeight(38)
        style_combo(self.combo_model)
        self.combo_model.currentIndexChanged.connect(self._on_model_changed)
        self.layout_main.addWidget(self.combo_model)

        # Model description label
        self.model_desc_label = QLabel()
        self.model_desc_label.setStyleSheet(
            "color: #4f8cff; font-size: 10px; padding: 2px 4px;"
        )
        self.model_desc_label.setWordWrap(True)
        self.layout_main.addWidget(self.model_desc_label)
        self._update_model_desc()

        # Platform
        platform_label = QLabel("Platform")
        platform_label.setStyleSheet("color: #8892A8; font-size: 11px;")
        self.layout_main.addWidget(platform_label)

        self.combo_platform = QComboBox()
        self.combo_platform.addItems(PLATFORMS)
        self.combo_platform.setMinimumHeight(38)
        style_combo(self.combo_platform)
        self.combo_platform.currentTextChanged.connect(self._on_platform_changed)
        self.layout_main.addWidget(self.combo_platform)

        # Keyword Style
        self.keyword_style_label = QLabel("Keyword Style")
        self.keyword_style_label.setStyleSheet("color: #8892A8; font-size: 11px;")
        self.layout_main.addWidget(self.keyword_style_label)

        self.combo_keyword_style = QComboBox()
        self.combo_keyword_style.addItems(KEYWORD_STYLES)
        self.combo_keyword_style.setMinimumHeight(38)
        style_combo(self.combo_keyword_style)
        self.combo_keyword_style.currentTextChanged.connect(
            self.keyword_style_changed.emit
        )
        self.layout_main.addWidget(self.combo_keyword_style)

        # Initially hide keyword style for iStock
        self._update_keyword_style_visibility()

        # ── METADATA ──
        self.layout_main.addSpacing(4)
        self.layout_main.addWidget(SectionDivider("Metadata"))

        # Keywords slider
        self.slider_keywords = SliderRow("Keywords", SLIDER_CONFIGS["keywords"])
        self.slider_keywords.value_changed.connect(self.keywords_changed.emit)
        self.layout_main.addWidget(self.slider_keywords)

        # Title Length slider
        self.slider_title = SliderRow("Title Length", SLIDER_CONFIGS["title_length"])
        self.slider_title.value_changed.connect(self.title_length_changed.emit)
        self.layout_main.addWidget(self.slider_title)

        # Description slider
        self.slider_desc = SliderRow("Description", SLIDER_CONFIGS["description"])
        self.slider_desc.value_changed.connect(self.description_changed.emit)
        self.layout_main.addWidget(self.slider_desc)

        # Spacer
        self.layout_main.addStretch(1)

        # Debug Log button
        self.btn_debug = QPushButton("\U0001F4CB Debug Log")
        self.btn_debug.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_debug.clicked.connect(self._on_debug_log)
        self.layout_main.addWidget(self.btn_debug)

        scroll.setWidget(content)

        # Set scroll as the main layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _on_model_changed(self, index: int):
        model_id = self.combo_model.itemData(index)
        self._update_model_desc()
        self.model_changed.emit(model_id or "")

    def _update_model_desc(self):
        model_id = self.combo_model.currentData()
        info = AI_MODEL_INFO.get(model_id, {})
        desc = info.get("description", "")
        supports_cache = info.get("supports_cache", False)
        cache_tag = " ⚡Cache" if supports_cache else ""
        self.model_desc_label.setText(f"{desc}{cache_tag}")

    def _on_platform_changed(self, text: str):
        self.platform_changed.emit(text)
        self._update_keyword_style_visibility()

    def _update_keyword_style_visibility(self):
        is_istock = "iStock" in self.combo_platform.currentText()
        self.keyword_style_label.setVisible(not is_istock)
        self.combo_keyword_style.setVisible(not is_istock)

    def _on_save_key(self):
        key = self.api_key_input.text().strip()
        if key:
            self.api_key_saved.emit(key)

    def _on_clear_key(self):
        self.api_key_input.clear()
        self.api_key_cleared.emit()

    def _on_debug_log(self):
        """Open debug log file with system default application."""
        if os.path.exists(DEBUG_LOG_PATH):
            if platform.system() == "Darwin":
                subprocess.Popen(["open", DEBUG_LOG_PATH])
            elif platform.system() == "Windows":
                os.startfile(DEBUG_LOG_PATH)
            else:
                subprocess.Popen(["xdg-open", DEBUG_LOG_PATH])

    def set_api_key(self, key: str):
        """Pre-fill API key from keyring."""
        self.api_key_input.setText(key)

    def get_api_key(self) -> str:
        return self.api_key_input.text().strip()

    def get_model(self) -> str:
        """Return model ID (e.g. 'gemini-2.5-flash'), not display label."""
        return self.combo_model.currentData() or self.combo_model.currentText()

    def get_platform(self) -> str:
        return self.combo_platform.currentText()

    def get_platform_name(self) -> str:
        """Return platform name."""
        return self.combo_platform.currentText()

    def get_platform_rate(self) -> dict:
        """Return credit rates {photo, video} for current platform from server config."""
        from core.config import PLATFORM_RATES
        name = self.get_platform_name()
        rates = PLATFORM_RATES.get(name, {"photo": 3, "video": 3})
        # Backward compat: if old int format somehow remains
        if isinstance(rates, int):
            return {"photo": rates, "video": rates}
        return rates

    def get_keyword_style(self) -> str:
        return self.combo_keyword_style.currentText()

    def get_settings(self) -> dict:
        """Return all current sidebar settings."""
        return {
            "model": self.get_model(),
            "platform": self.get_platform_name(),
            "platform_rate": self.get_platform_rate(),
            "keyword_style": self.get_keyword_style(),
            "max_keywords": self.slider_keywords.get_value(),
            "title_length": self.slider_title.get_value(),
            "description_length": self.slider_desc.get_value(),
        }

    def set_processing(self, is_processing: bool):
        """Lock/unlock all controls during processing."""
        self.api_key_input.setEnabled(not is_processing)
        self.btn_save_key.setEnabled(not is_processing)
        self.btn_clear_key.setEnabled(not is_processing)
        self.combo_model.setEnabled(not is_processing)
        self.combo_platform.setEnabled(not is_processing)
        self.combo_keyword_style.setEnabled(not is_processing)
        self.slider_keywords.slider.setEnabled(not is_processing)
        self.slider_title.slider.setEnabled(not is_processing)
        self.slider_desc.slider.setEnabled(not is_processing)
