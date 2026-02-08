"""
BigEye Pro — Center Stage / Gallery Component
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QProgressBar,
    QFrame, QSizePolicy, QAbstractItemView
)
from PySide6.QtCore import (
    Qt, Signal, QSize, QThread, QObject, QRunnable,
    QThreadPool, Slot
)
from PySide6.QtGui import (
    QPixmap, QImage, QIcon, QPainter, QColor, QBrush, QPen,
    QFont, QLinearGradient, QRadialGradient
)

from core.config import THUMBNAIL_SIZE, ALL_EXTENSIONS
from utils.helpers import scan_folder, count_files, is_video, is_image, format_number
from utils.video_thumb import extract_first_frame


class ThumbnailLoader(QRunnable):
    """Async thumbnail loader using QThreadPool."""

    class Signals(QObject):
        loaded = Signal(str, QPixmap)  # filepath, pixmap

    def __init__(self, filepath: str, size: int = THUMBNAIL_SIZE):
        super().__init__()
        self.filepath = filepath
        self.size = size
        self.signals = self.Signals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        try:
            load_path = self.filepath

            # For video files, extract first frame via FFmpeg
            if is_video(self.filepath):
                frame_path = extract_first_frame(self.filepath)
                if frame_path:
                    load_path = frame_path
                else:
                    return  # Cannot extract frame

            pixmap = QPixmap(load_path)
            if pixmap.isNull():
                img = QImage(load_path)
                if not img.isNull():
                    pixmap = QPixmap.fromImage(img)

            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    self.size, self.size,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                # Center crop
                if pixmap.width() > self.size or pixmap.height() > self.size:
                    x = (pixmap.width() - self.size) // 2
                    y = (pixmap.height() - self.size) // 2
                    pixmap = pixmap.copy(x, y, self.size, self.size)

                self.signals.loaded.emit(self.filepath, pixmap)
        except Exception:
            pass


def create_thumbnail_icon(
    pixmap: QPixmap,
    filename: str,
    file_type: str,
    status: str = "pending",
    size: int = THUMBNAIL_SIZE
) -> QPixmap:
    """Create a styled thumbnail with overlays."""
    canvas = QPixmap(size, size)
    canvas.fill(QColor("#16213E"))

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Draw rounded rect clip for image
    from PySide6.QtGui import QPainterPath
    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, 10, 10)
    painter.setClipPath(path)

    # Draw image
    if not pixmap.isNull():
        painter.drawPixmap(0, 0, pixmap)
    else:
        painter.fillRect(0, 0, size, size, QColor("#0F3460"))

    # Error state: dim + desaturate
    if status == "error":
        painter.fillRect(0, 0, size, size, QColor(0, 0, 0, 120))

    # Bottom gradient overlay for filename
    grad = QLinearGradient(0, size - 35, 0, size)
    grad.setColorAt(0.0, QColor(0, 0, 0, 0))
    grad.setColorAt(1.0, QColor(0, 0, 0, 180))
    painter.fillRect(0, size - 35, size, 35, QBrush(grad))

    # Filename text
    painter.setPen(QColor("#E8E8E8"))
    font = QFont("Helvetica Neue", 8)
    painter.setFont(font)
    # Truncate filename
    display_name = filename
    if len(display_name) > 16:
        display_name = display_name[:13] + "..."
    painter.drawText(4, size - 8, display_name)

    # Type badge (bottom-right)
    badge_text = "VID" if file_type == "video" else "IMG"
    badge_color = QColor("#7B2FFF") if file_type == "video" else QColor("#00B4D8")
    badge_w, badge_h = 28, 16
    badge_x = size - badge_w - 4
    badge_y = size - 38

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(badge_color)
    painter.drawRoundedRect(badge_x, badge_y, badge_w, badge_h, 4, 4)
    painter.setPen(QColor("#FFFFFF"))
    font.setPointSize(7)
    font.setWeight(QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(badge_x, badge_y, badge_w, badge_h,
                     Qt.AlignmentFlag.AlignCenter, badge_text)

    # Video play overlay
    if file_type == "video" and status == "pending":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 100))
        cx, cy = size // 2, size // 2 - 10
        painter.drawEllipse(cx - 16, cy - 16, 32, 32)
        painter.setBrush(QColor("#FFFFFF"))
        # Triangle
        from PySide6.QtGui import QPolygonF
        from PySide6.QtCore import QPointF
        triangle = QPolygonF([
            QPointF(cx - 6, cy - 8),
            QPointF(cx - 6, cy + 8),
            QPointF(cx + 8, cy),
        ])
        painter.drawPolygon(triangle)

    # Status badges
    if status == "completed":
        # Green circle with checkmark top-right
        bx, by = size - 22, 6
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#00E396"))
        painter.drawEllipse(bx, by, 16, 16)
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.drawLine(bx + 4, by + 8, bx + 7, by + 11)
        painter.drawLine(bx + 7, by + 11, bx + 12, by + 5)

    elif status == "error":
        # Red circle with X top-right
        bx, by = size - 22, 6
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FF4560"))
        painter.drawEllipse(bx, by, 16, 16)
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.drawLine(bx + 4, by + 4, bx + 12, by + 12)
        painter.drawLine(bx + 12, by + 4, bx + 4, by + 12)

    elif status == "processing":
        # Dark overlay + "Processing" text
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 140))
        painter.drawRect(0, 0, size, size)
        painter.setPen(QColor("#FEB019"))
        font = QFont("Helvetica Neue", 9)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(0, 0, size, size,
                         Qt.AlignmentFlag.AlignCenter, "Processing")

    painter.end()
    return canvas


class Gallery(QWidget):
    """Center stage with toolbar, gallery grid, cost bar, and action bar."""

    file_selected = Signal(str)  # filepath
    start_clicked = Signal()
    stop_clicked = Signal()
    folder_changed = Signal(str, list)  # folder_path, file_list

    def __init__(self, parent=None):
        super().__init__(parent)
        self._folder_path = ""
        self._file_list = []
        self._file_statuses = {}  # filepath -> status
        self._thumbnails = {}  # filepath -> QPixmap
        self._thread_pool = QThreadPool()
        self._thread_pool.setMaxThreadCount(4)
        self._is_processing = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── TOOLBAR ──
        toolbar = QWidget()
        toolbar.setStyleSheet("background: #16213E; border-bottom: 1px solid #1A3A6B;")
        toolbar.setFixedHeight(44)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 0, 12, 0)
        toolbar_layout.setSpacing(10)

        self.btn_open = QPushButton("\U0001F4C2 Open Folder")
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.clicked.connect(self._on_open_folder)
        toolbar_layout.addWidget(self.btn_open)

        self.path_label = QLabel("No folder selected")
        self.path_label.setStyleSheet(
            "color: #4A5568; font-size: 12px; background: #16213E; "
            "padding: 4px 8px; border-radius: 4px;"
        )
        self.path_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        toolbar_layout.addWidget(self.path_label)

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #8892A8; font-size: 12px;")
        toolbar_layout.addWidget(self.stats_label)

        layout.addWidget(toolbar)

        # ── GALLERY GRID ──
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_widget.setIconSize(QSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE))
        self.list_widget.setGridSize(QSize(THUMBNAIL_SIZE + 10, THUMBNAIL_SIZE + 10))
        self.list_widget.setSpacing(10)
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.setWrapping(True)
        self.list_widget.setMovement(QListWidget.Movement.Static)
        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: #1A1A2E;
                border: none;
                padding: 10px;
            }
            QListWidget::item:selected {
                background: transparent;
                border: 2px solid #FF00CC;
                border-radius: 10px;
            }
        """)
        self.list_widget.currentItemChanged.connect(self._on_item_selected)
        layout.addWidget(self.list_widget, 1)

        # ── COST ESTIMATE BAR ──
        self.cost_bar = QWidget()
        self.cost_bar.setFixedHeight(32)
        self.cost_bar.setStyleSheet("background: #16213E88;")
        cost_layout = QHBoxLayout(self.cost_bar)
        cost_layout.setContentsMargins(12, 0, 12, 0)

        self.cost_label = QLabel("")
        self.cost_label.setStyleSheet("color: #8892A8; font-size: 12px;")
        cost_layout.addWidget(self.cost_label)

        cost_layout.addStretch()

        self.cost_status = QLabel("")
        self.cost_status.setStyleSheet("font-size: 12px;")
        cost_layout.addWidget(self.cost_status)

        layout.addWidget(self.cost_bar)

        # ── ACTION BAR ──
        action_bar = QWidget()
        action_bar.setStyleSheet(
            "background: #16213E; border-top: 1px solid #1A3A6B;"
        )
        action_layout = QVBoxLayout(action_bar)
        action_layout.setContentsMargins(16, 10, 16, 10)
        action_layout.setSpacing(8)

        # Progress row
        progress_row = QHBoxLayout()
        self.progress_text = QLabel("")
        self.progress_text.setStyleSheet("color: #8892A8; font-size: 12px;")
        progress_row.addWidget(self.progress_text)

        progress_row.addStretch()

        self.progress_percent = QLabel("")
        self.progress_percent.setStyleSheet("color: #E8E8E8; font-size: 12px; font-weight: 600;")
        progress_row.addWidget(self.progress_percent)

        action_layout.addLayout(progress_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        action_layout.addWidget(self.progress_bar)

        # START / STOP button
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_start = QPushButton("START")
        self.btn_start.setObjectName("startButton")
        self.btn_start.setFixedWidth(220)
        self.btn_start.setMinimumHeight(44)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setStyleSheet("""
            QPushButton#startButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FF00CC, stop:1 #7B2FFF);
                border: none;
                border-radius: 22px;
                padding: 12px 30px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QPushButton#startButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FF33DD, stop:1 #9B4FFF);
            }
            QPushButton#startButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #CC00AA, stop:1 #6622CC);
            }
            QPushButton#startButton:disabled {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FF00CC44, stop:1 #7B2FFF44);
                color: #FFFFFF88;
            }
        """)
        self.btn_start.clicked.connect(self.start_clicked.emit)
        btn_row.addWidget(self.btn_start)

        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setObjectName("stopButton")
        self.btn_stop.setFixedWidth(220)
        self.btn_stop.setMinimumHeight(44)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setStyleSheet("""
            QPushButton#stopButton {
                background: #FF4560;
                border: none;
                border-radius: 22px;
                padding: 12px 30px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QPushButton#stopButton:hover {
                background: #FF6B7F;
            }
            QPushButton#stopButton:pressed {
                background: #CC3750;
            }
        """)
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        self.btn_stop.hide()
        btn_row.addWidget(self.btn_stop)

        btn_row.addStretch()
        action_layout.addLayout(btn_row)

        layout.addWidget(action_bar)

    def _on_open_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder", "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.set_folder(folder)

    def set_folder(self, folder_path: str):
        """Load a folder and populate the gallery."""
        self._folder_path = folder_path
        self._file_list = scan_folder(folder_path)
        self._file_statuses = {f: "pending" for f in self._file_list}
        self._thumbnails = {}

        # Update path display
        display_path = folder_path
        if len(display_path) > 50:
            parts = display_path.split(os.sep)
            display_path = os.sep.join(parts[:2]) + "/.../" + os.sep.join(parts[-2:])
        self.path_label.setText(display_path)
        self.path_label.setStyleSheet(
            "color: #8892A8; font-size: 12px; background: #16213E; "
            "padding: 4px 8px; border-radius: 4px;"
        )

        # Update stats
        img_count, vid_count = count_files(self._file_list)
        self.stats_label.setText(f"\U0001F4F8{img_count} \U0001F3AC{vid_count}")

        # Populate grid
        self._populate_grid()

        # Emit signal
        self.folder_changed.emit(folder_path, self._file_list)

    def _populate_grid(self):
        """Populate the gallery grid with thumbnails."""
        self.list_widget.clear()

        for filepath in self._file_list:
            filename = os.path.basename(filepath)
            file_type = "video" if is_video(filepath) else "image"
            status = self._file_statuses.get(filepath, "pending")

            # Create placeholder item
            placeholder = create_thumbnail_icon(
                QPixmap(), filename, file_type, status
            )
            item = QListWidgetItem()
            item.setIcon(QIcon(placeholder))
            item.setSizeHint(QSize(THUMBNAIL_SIZE + 10, THUMBNAIL_SIZE + 10))
            item.setData(Qt.ItemDataRole.UserRole, filepath)
            item.setToolTip(filename)
            self.list_widget.addItem(item)

            # Load real thumbnail async (images + videos)
            loader = ThumbnailLoader(filepath)
            loader.signals.loaded.connect(self._on_thumbnail_loaded)
            self._thread_pool.start(loader)

    def _on_thumbnail_loaded(self, filepath: str, pixmap: QPixmap):
        """Update thumbnail when async load completes."""
        self._thumbnails[filepath] = pixmap
        filename = os.path.basename(filepath)
        file_type = "video" if is_video(filepath) else "image"
        status = self._file_statuses.get(filepath, "pending")

        icon_pixmap = create_thumbnail_icon(pixmap, filename, file_type, status)

        # Find and update the item
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == filepath:
                item.setIcon(QIcon(icon_pixmap))
                break

    def _on_item_selected(self, current, previous):
        if current:
            filepath = current.data(Qt.ItemDataRole.UserRole)
            if filepath:
                self.file_selected.emit(filepath)

    def update_file_status(self, filepath: str, status: str):
        """Update a file's status and refresh its thumbnail."""
        self._file_statuses[filepath] = status
        filename = os.path.basename(filepath)
        file_type = "video" if is_video(filepath) else "image"
        pixmap = self._thumbnails.get(filepath, QPixmap())

        icon_pixmap = create_thumbnail_icon(pixmap, filename, file_type, status)

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == filepath:
                item.setIcon(QIcon(icon_pixmap))
                break

    def reset_file_statuses(self):
        """Reset all file statuses to 'pending' and refresh thumbnails."""
        for filepath in self._file_list:
            self._file_statuses[filepath] = "pending"
            filename = os.path.basename(filepath)
            file_type = "video" if is_video(filepath) else "image"
            pixmap = self._thumbnails.get(filepath, QPixmap())
            icon_pixmap = create_thumbnail_icon(pixmap, filename, file_type, "pending")
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == filepath:
                    item.setIcon(QIcon(icon_pixmap))
                    break

    def update_cost_estimate(self, photo_count: int, video_count: int,
                             photo_rate: int, video_rate: int,
                             platform: str, balance: int):
        """Update the cost estimate bar with separate photo/video rates."""
        file_count = photo_count + video_count
        cost = (photo_count * photo_rate) + (video_count * video_rate)
        # Build rate label
        if photo_rate == video_rate:
            rate_label = f"{platform} \u00D7 {photo_rate}"
        else:
            rate_label = f"{platform}: \U0001F4F7{photo_rate} \U0001F3AC{video_rate}"
        self.cost_label.setText(
            f"\U0001F4C1 {file_count} files \u00B7 \u2248 {format_number(cost)} credits "
            f"\u00B7 ({rate_label})"
        )
        if balance >= cost:
            self.cost_status.setText("\u2713 Sufficient")
            self.cost_status.setStyleSheet("color: #00E396; font-size: 12px; font-weight: 600;")
        else:
            self.cost_status.setText("\u2715 Insufficient")
            self.cost_status.setStyleSheet("color: #FF4560; font-size: 12px; font-weight: 600;")

    def update_progress(self, current: int, total: int):
        """Update progress bar and text."""
        if total == 0:
            return
        pct = int((current / total) * 100)
        self.progress_bar.setValue(pct)
        self.progress_text.setText(f"Processing {current}/{total}")
        self.progress_percent.setText(f"{pct}%")

    def reset_progress(self):
        """Reset progress bar."""
        self.progress_bar.setMaximum(100)  # restore determinate mode
        self.progress_bar.setValue(0)
        self.progress_text.setText("")
        self.progress_percent.setText("")

    def set_processing(self, is_processing: bool):
        """Lock/unlock controls during processing."""
        self._is_processing = is_processing
        self.btn_open.setEnabled(not is_processing)
        self.btn_start.setVisible(not is_processing)
        self.btn_stop.setVisible(is_processing)

    def get_file_list(self) -> list:
        return self._file_list

    def get_folder_path(self) -> str:
        return self._folder_path

    def get_file_count(self) -> int:
        return len(self._file_list)
