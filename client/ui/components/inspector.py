"""
BigEye Pro — Right Inspector Panel
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage, QFont, QColor, QPainter, QPainterPath

from core.config import INSPECTOR_WIDTH
from utils.helpers import is_video, format_number
from utils.video_thumb import extract_first_frame


class InspectorPreview(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(190)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "background: #16213E; border: 1px solid #1A3A6B; border-radius: 10px;"
            " color: #4A5568; font-size: 12px;"
        )
        self._status = ""
        self._pixmap_src = None
        self._is_video = False

    def set_image(self, filepath: str):
        if not filepath or not os.path.exists(filepath):
            self._pixmap_src = None
            self._is_video = False
            self.setText("No Preview")
            return

        self._is_video = is_video(filepath)
        load_path = filepath

        # For video files, extract first frame via FFmpeg
        if self._is_video:
            frame_path = extract_first_frame(filepath)
            if frame_path:
                load_path = frame_path
            else:
                self._pixmap_src = None
                self.setText("Cannot load preview")
                return

        px = QPixmap(load_path)
        if px.isNull():
            img = QImage(load_path)
            if not img.isNull():
                px = QPixmap.fromImage(img)
        if not px.isNull():
            self._pixmap_src = px.scaled(
                self.width() - 2, 188,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            self._draw()
        else:
            self._pixmap_src = None
            self.setText("Cannot load preview")

    def set_status(self, status: str):
        self._status = status
        if self._pixmap_src:
            self._draw()

    def _draw(self):
        if not self._pixmap_src:
            return
        w, h = self.width() - 2, 188
        canvas = QPixmap(w, h)
        canvas.fill(QColor("#16213E"))
        p = QPainter(canvas)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, 10, 10)
        p.setClipPath(path)
        px = self._pixmap_src
        p.drawPixmap((w - px.width()) // 2, (h - px.height()) // 2, px)
        # Play overlay for videos
        if self._is_video and self._status in ("", "pending"):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 100))
            cx, cy = w // 2, h // 2
            p.drawEllipse(cx - 22, cy - 22, 44, 44)
            p.setBrush(QColor("#FFFFFF"))
            from PySide6.QtGui import QPolygonF
            from PySide6.QtCore import QPointF
            triangle = QPolygonF([
                QPointF(cx - 8, cy - 12),
                QPointF(cx - 8, cy + 12),
                QPointF(cx + 12, cy),
            ])
            p.drawPolygon(triangle)

        if self._status == "completed":
            self._draw_badge(p, w, "\u2713 Done", QColor("#00E396"))
        elif self._status == "error":
            self._draw_badge(p, w, "Error", QColor("#FF4560"))
        p.end()
        self.setPixmap(canvas)

    def _draw_badge(self, p, w, text, color):
        font = QFont("Helvetica Neue", 9)
        font.setWeight(QFont.Weight.Bold)
        p.setFont(font)
        tw = p.fontMetrics().horizontalAdvance(text) + 12
        bx, by = w - tw - 8, 8
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(bx, by, tw, 20, 6, 6)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(bx, by, tw, 20, Qt.AlignmentFlag.AlignCenter, text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap_src:
            self._draw()


class Inspector(QWidget):
    export_clicked = Signal()
    metadata_edited = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(INSPECTOR_WIDTH)
        self._current_file = ""
        self._results = {}
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.preview = InspectorPreview()
        layout.addWidget(self.preview)
        layout.addSpacing(4)

        self.filename_label = QLabel("No file selected")
        self.filename_label.setStyleSheet("color: #4A5568; font-size: 12px;")
        self.filename_label.setWordWrap(True)
        layout.addWidget(self.filename_label)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #8892A8; font-size: 11px;")
        layout.addWidget(self.info_label)
        layout.addSpacing(4)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.hide()
        layout.addWidget(self.status_label)

        # Edit fields container
        self.edit_container = QWidget()
        el = QVBoxLayout(self.edit_container)
        el.setContentsMargins(0, 0, 0, 0)
        el.setSpacing(6)

        el.addWidget(self._make_label("Title"))
        self.title_edit = QLineEdit()
        self.title_edit.setMinimumHeight(36)
        self.title_edit.editingFinished.connect(self._on_edit)
        el.addWidget(self.title_edit)

        el.addWidget(self._make_label("Description"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setFixedHeight(70)
        el.addWidget(self.desc_edit)

        self.keywords_label = QLabel("Keywords (0)")
        self.keywords_label.setStyleSheet("color: #8892A8; font-size: 11px;")
        el.addWidget(self.keywords_label)
        self.keywords_edit = QTextEdit()
        self.keywords_edit.setFixedHeight(110)
        el.addWidget(self.keywords_edit)

        self.edit_container.hide()
        layout.addWidget(self.edit_container)
        layout.addStretch(1)

        self.btn_export = QPushButton("\U0001F4BE Export CSV")
        self.btn_export.setObjectName("exportButton")
        self.btn_export.setMinimumHeight(38)
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.clicked.connect(self.export_clicked.emit)
        layout.addWidget(self.btn_export)

        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _make_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #8892A8; font-size: 11px;")
        return lbl

    def _on_edit(self):
        if not self._current_file:
            return
        data = {
            "title": self.title_edit.text(),
            "description": self.desc_edit.toPlainText(),
            "keywords": [k.strip() for k in self.keywords_edit.toPlainText().split(",") if k.strip()],
        }
        self.metadata_edited.emit(self._current_file, data)

    def set_results_ref(self, results: dict):
        self._results = results

    def show_file(self, filepath: str):
        self._current_file = filepath
        filename = os.path.basename(filepath)
        self.filename_label.setText(filename)
        self.filename_label.setStyleSheet("color: #E8E8E8; font-size: 12px; font-weight: 700;")
        file_type = "\U0001F3AC Video" if is_video(filepath) else "\U0001F4F7 Photo"
        self.preview.set_image(filepath)

        result = self._results.get(filename, {})
        status = result.get("status", "pending")
        self.preview.set_status(status)

        token_text = ""
        if "token_input" in result:
            token_text = f"  Tokens: {format_number(result['token_input'])}/{format_number(result['token_output'])}"
        self.info_label.setText(f"{file_type}{token_text}")

        if status == "completed" or status == "success":
            self.status_label.hide()
            self.edit_container.show()
            self.title_edit.setText(result.get("title", ""))
            self.desc_edit.setPlainText(result.get("description", ""))
            kw = result.get("keywords", [])
            if isinstance(kw, list):
                kw = ", ".join(kw)
            self.keywords_edit.setPlainText(kw)
            count = len([k for k in kw.split(",") if k.strip()]) if kw else 0
            self.keywords_label.setText(f"Keywords ({count})")
        elif status == "processing":
            self.edit_container.hide()
            self.status_label.setText("Processing...")
            self.status_label.setStyleSheet("color: #FEB019; font-size: 12px; padding: 8px;")
            self.status_label.show()
        elif status == "error":
            self.edit_container.hide()
            err = result.get("error", "Unknown error")
            self.status_label.setText(f"\u26A0\uFE0F {err}")
            self.status_label.setStyleSheet(
                "color: #FF4560; font-size: 12px; padding: 8px; "
                "background: #FF456015; border-radius: 8px;"
            )
            self.status_label.show()
        else:
            self.edit_container.hide()
            self.status_label.setText("Pending")
            self.status_label.setStyleSheet("color: #4A5568; font-size: 12px; padding: 8px;")
            self.status_label.show()

    def set_processing(self, is_processing: bool):
        self.title_edit.setReadOnly(is_processing)
        self.desc_edit.setReadOnly(is_processing)
        self.keywords_edit.setReadOnly(is_processing)

    def clear(self):
        self._current_file = ""
        self.filename_label.setText("No file selected")
        self.filename_label.setStyleSheet("color: #4A5568; font-size: 12px;")
        self.info_label.setText("")
        self.status_label.hide()
        self.edit_container.hide()
        self.preview.setText("No Preview")
        self.preview._pixmap_src = None
