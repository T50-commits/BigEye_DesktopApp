"""
BigEye Pro — Main Window (Task B-05)
Assembles Top Bar, Sidebar, Gallery (Center Stage), and Inspector.
3-column layout: Sidebar(270px) | Gallery(stretch) | Inspector(300px)
"""
import logging
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QStatusBar, QMessageBox, QSplitter, QFrame
)
from PySide6.QtCore import Qt, QTimer, QThread, QObject, Slot, Signal
from PySide6.QtGui import QAction, QKeySequence

from core.config import (
    MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT,
    MAIN_WINDOW_MIN_WIDTH, MAIN_WINDOW_MIN_HEIGHT,
    APP_NAME, APP_VERSION, STATUS_BAR_HEIGHT,
    KEYRING_SERVICE, KEYRING_API_KEY,
)
from core.auth_manager import AuthManager
from core.api_client import api, APIError, NetworkError, MaintenanceError, UpdateRequiredError
from core.job_manager import JobManager
from core.managers.journal_manager import JournalManager
from utils.helpers import count_files, format_number
from utils.security import get_hardware_id, save_to_keyring, load_from_keyring, delete_from_keyring
from ui.components.credit_bar import CreditBar
from ui.components.sidebar import Sidebar
from ui.components.gallery import Gallery
from ui.components.inspector import Inspector
from ui.components.confirm_dialog import ConfirmDialog
from ui.components.insufficient_dialog import InsufficientDialog
from ui.components.export_csv_dialog import ExportCsvDialog
from ui.components.summary_dialog import SummaryDialog
from ui.components.history_dialog import HistoryDialog
from ui.components.topup_dialog import TopUpDialog
from ui.components.update_dialog import UpdateDialog
from ui.components.recovery_dialog import RecoveryDialog
from ui.components.maintenance_dialog import MaintenanceDialog

logger = logging.getLogger("bigeye")


class StartupWorker(QObject):
    """Runs startup tasks in background: update check, recovery, balance."""
    balance_loaded = Signal(int)
    promos_loaded = Signal(list)
    rates_loaded = Signal(dict)
    bank_info_loaded = Signal(dict)
    update_available = Signal(dict)
    recovery_found = Signal(dict)
    maintenance = Signal(str)
    finished = Signal()

    def __init__(self, auth_manager=None, parent=None):
        super().__init__(parent)
        self._auth_manager = auth_manager

    @Slot()
    def run(self):
        # 1. Check for update
        try:
            hw_id = get_hardware_id()
            result = api.check_update(APP_VERSION, hw_id)
            if result.get("update_available"):
                self.update_available.emit(result)
        except UpdateRequiredError as e:
            self.update_available.emit({
                "version": e.version, "download_url": e.download_url,
                "force": True, "message": str(e),
            })
        except MaintenanceError as e:
            self.maintenance.emit(str(e))
        except Exception as e:
            logger.debug(f"Update check skipped: {e}")

        # 2. Crash recovery
        try:
            recovery = JournalManager.recover_on_startup(api)
            if recovery:
                self.recovery_found.emit(recovery)
        except Exception as e:
            logger.debug(f"Recovery check skipped: {e}")

        # 3. Cleanup orphaned caches
        try:
            GeminiEngine().cleanup_orphaned_caches()
        except Exception as e:
            logger.debug(f"Cache cleanup skipped: {e}")

        # 4. Load balance + promos + credit rates
        from core.api_client import AuthenticationError as _AuthErr
        from core.auth_manager import AuthManager as _AM
        try:
            data = api.get_balance_with_promos()
            self.balance_loaded.emit(data.get("credits", 0))
            self.promos_loaded.emit(data.get("active_promos", []))
            self.rates_loaded.emit(data.get("credit_rates", {}))
            self.bank_info_loaded.emit(data.get("bank_info", {}))
        except _AuthErr:
            # Token expired — try auto re-login with saved credentials then retry
            _am = self._auth_manager or _AM()
            if _am.try_auto_relogin():
                try:
                    data = api.get_balance_with_promos()
                    self.balance_loaded.emit(data.get("credits", 0))
                    self.promos_loaded.emit(data.get("active_promos", []))
                    self.rates_loaded.emit(data.get("credit_rates", {}))
                    self.bank_info_loaded.emit(data.get("bank_info", {}))
                except Exception as e:
                    logger.warning(f"Balance load failed after re-login: {e}")
            else:
                logger.warning("Auto re-login failed — user must login manually")
        except Exception as e:
            logger.debug(f"Balance load skipped: {e}")

        self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self, user_name: str = "", jwt_token: str = "",
                 auth_manager: AuthManager | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(APP_NAME)
        self.resize(MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT)
        self.setMinimumSize(MAIN_WINDOW_MIN_WIDTH, MAIN_WINDOW_MIN_HEIGHT)

        self._jwt_token = jwt_token
        self._user_name = user_name
        self._auth_manager = auth_manager or AuthManager()
        self._results = {}  # filename -> result dict
        self._is_processing = False
        self._startup_thread = None
        self._startup_worker = None
        self._job_manager = JobManager()
        self._job_thread = None

        self._setup_ui()
        self._setup_shortcuts()
        self._connect_signals()
        self._init_state()
        self._run_startup_tasks()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── TOP BAR ──
        self.credit_bar = CreditBar()
        main_layout.addWidget(self.credit_bar)

        # ── BODY (Sidebar | Gallery | Inspector) ──
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Left sidebar
        self.sidebar = Sidebar()
        body_layout.addWidget(self.sidebar)

        # Vertical divider
        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.VLine)
        div1.setStyleSheet("color: #1A3A6B;")
        body_layout.addWidget(div1)

        # Center gallery
        self.gallery = Gallery()
        body_layout.addWidget(self.gallery, 1)  # stretch

        # Vertical divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.VLine)
        div2.setStyleSheet("color: #1A3A6B;")
        body_layout.addWidget(div2)

        # Right inspector
        self.inspector = Inspector()
        self.inspector.set_results_ref(self._results)
        body_layout.addWidget(self.inspector)

        main_layout.addWidget(body, 1)

        # ── STATUS BAR ──
        self.status_bar = QStatusBar()
        self.status_bar.setFixedHeight(STATUS_BAR_HEIGHT)
        self.status_bar.setStyleSheet(
            "QStatusBar { background: #16213E; color: #4A5568; "
            "font-size: 11px; border-top: 1px solid #1A3A6B; }"
        )
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        # Version label on right side
        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setStyleSheet("color: #4A5568; font-size: 11px; padding-right: 8px;")
        self.status_bar.addPermanentWidget(version_label)

    def _setup_shortcuts(self):
        shortcuts = [
            ("Ctrl+O", self._on_open_folder),
            ("Ctrl+Return", self._on_start_stop),
            ("Ctrl+S", self._on_export_csv),
            ("Ctrl+R", self._on_refresh_balance),
            ("Ctrl+T", self._on_topup),
            ("Ctrl+H", self._on_history),
            ("Escape", self._on_escape),
        ]
        for key, callback in shortcuts:
            action = QAction(self)
            action.setShortcut(QKeySequence(key))
            action.triggered.connect(callback)
            self.addAction(action)

    def _connect_signals(self):
        # Credit bar
        self.credit_bar.topup_clicked.connect(self._on_topup)
        self.credit_bar.refresh_clicked.connect(self._on_refresh_balance)
        self.credit_bar.history_clicked.connect(self._on_history)
        self.credit_bar.logout_clicked.connect(self._on_logout)

        # Sidebar
        self.sidebar.platform_changed.connect(self._on_platform_changed)
        self.sidebar.keyword_style_changed.connect(self._on_keyword_style_changed)
        self.sidebar.api_key_saved.connect(self._on_save_api_key)
        self.sidebar.api_key_cleared.connect(self._on_clear_api_key)

        # Gallery
        self.gallery.file_selected.connect(self._on_file_selected)
        self.gallery.start_clicked.connect(self._on_start)
        self.gallery.stop_clicked.connect(self._on_stop)
        self.gallery.folder_changed.connect(self._on_folder_changed)

        # Inspector
        self.inspector.export_clicked.connect(self._on_export_csv)
        self.inspector.metadata_edited.connect(self._on_metadata_edited)

    def _init_state(self):
        """Initialize state after window is shown."""
        self.credit_bar.set_user_name(self._user_name)
        self.credit_bar.set_balance(0)  # Will be updated by startup worker
        self.status_bar.showMessage("Ready")

        # Load saved API key from keyring
        saved_key = load_from_keyring(KEYRING_SERVICE, KEYRING_API_KEY)
        if saved_key:
            self.sidebar.set_api_key(saved_key)

    def _run_startup_tasks(self):
        """Run startup tasks in background thread."""
        self._startup_worker = StartupWorker(auth_manager=self._auth_manager)
        self._startup_thread = QThread()
        self._startup_worker.moveToThread(self._startup_thread)

        self._startup_thread.started.connect(self._startup_worker.run)
        self._startup_worker.balance_loaded.connect(self.credit_bar.set_balance)
        self._startup_worker.promos_loaded.connect(self.credit_bar.set_promos)
        self._startup_worker.rates_loaded.connect(self._on_rates_loaded)
        self._startup_worker.bank_info_loaded.connect(self._on_bank_info_loaded)
        self._startup_worker.update_available.connect(self._on_update_available)
        self._startup_worker.recovery_found.connect(self._on_recovery_found)
        self._startup_worker.maintenance.connect(self._on_maintenance)
        self._startup_worker.finished.connect(self._startup_thread.quit)
        self._startup_thread.finished.connect(self._cleanup_startup)

        self._startup_thread.start()
        logger.info("Startup tasks running in background")

    def _on_update_available(self, info: dict):
        dialog = UpdateDialog(
            info.get("version", ""),
            info.get("download_url", ""),
            info.get("force", False),
            self,
        )
        dialog.exec()

    def _on_recovery_found(self, info: dict):
        dialog = RecoveryDialog(info, self)
        dialog.exec()

    def _on_bank_info_loaded(self, bank_info: dict):
        """Store bank_info from server for use in TopUpDialog."""
        self._bank_info = bank_info

    def _on_maintenance(self, message: str):
        dialog = MaintenanceDialog(self, message=message, force_close=True)
        dialog.exec()

    def _cleanup_startup(self):
        if self._startup_worker:
            self._startup_worker.deleteLater()
            self._startup_worker = None
        if self._startup_thread:
            self._startup_thread.deleteLater()
            self._startup_thread = None

    # ── Slot Handlers ──

    def _on_open_folder(self):
        if not self._is_processing:
            self.gallery._on_open_folder()

    def _on_start_stop(self):
        if self._is_processing:
            self._on_stop()
        else:
            self._on_start()

    def _on_start(self):
        """Validate and start processing."""
        file_list = self.gallery.get_file_list()
        if not file_list:
            QMessageBox.warning(self, "ไม่พบไฟล์", "กรุณาเปิดโฟลเดอร์ที่มีไฟล์ภาพหรือวิดีโอก่อน")
            return

        api_key = self.sidebar.get_api_key()
        if not api_key:
            QMessageBox.warning(self, "ไม่พบ API Key", "กรุณากรอกและบันทึก Gemini API Key ก่อน")
            return

        settings = self.sidebar.get_settings()
        rates = settings["platform_rate"]  # {"photo": N, "video": N}
        photo_rate = rates["photo"]
        video_rate = rates["video"]
        file_count = len(file_list)
        balance = self.credit_bar.get_balance()

        img_count, vid_count = count_files(file_list)
        cost = (img_count * photo_rate) + (vid_count * video_rate)

        if balance < cost:
            dialog = InsufficientDialog(cost, balance, photo_rate, self)
            dialog.topup_requested.connect(self._on_topup)
            dialog.partial_requested.connect(self._on_partial_process)
            dialog.exec()
            return

        dialog = ConfirmDialog(
            file_count, img_count, vid_count,
            settings["model"], settings["platform"],
            cost, balance, self,
            photo_rate=photo_rate, video_rate=video_rate,
        )
        if dialog.exec() == ConfirmDialog.DialogCode.Accepted:
            self._begin_processing(file_list)

    def _on_partial_process(self, max_files: int):
        """Start processing with limited file count."""
        file_list = self.gallery.get_file_list()[:max_files]
        self._begin_processing(file_list)

    def _begin_processing(self, file_list: list):
        """Begin processing via JobManager on a background thread."""
        # Clear previous results before starting new job
        self._results.clear()
        self.inspector.clear()
        self.gallery.reset_file_statuses()

        self._is_processing = True
        self._set_processing_state(True)
        self.inspector.enable_export(False)
        self._process_total = len(file_list)

        # Show immediate feedback: indeterminate progress + "Preparing..."
        self.gallery.progress_bar.setMaximum(0)  # indeterminate animation
        self.gallery.progress_text.setText("กำลังตรวจสอบเครดิต...")
        self.gallery.progress_percent.setText("")
        self.status_bar.showMessage(f"กำลังตรวจสอบเครดิต... ({len(file_list)} ไฟล์)")

        # Fresh JobManager each run to avoid dead-thread affinity issues
        self._job_manager = JobManager()

        # Connect JobManager signals to UI
        self._job_manager.file_completed.connect(self._on_file_completed)
        self._job_manager.progress_updated.connect(self._on_progress_updated)
        self._job_manager.job_completed.connect(self._on_job_completed)
        self._job_manager.job_failed.connect(self._on_job_failed)
        self._job_manager.credit_updated.connect(self.credit_bar.set_balance)
        self._job_manager.status_update.connect(self._on_status_update)

        # Build settings dict for JobManager
        settings = self.sidebar.get_settings()
        settings["api_key"] = self.sidebar.get_api_key()
        settings["folder_path"] = self.gallery.get_folder_path()
        settings["balance"] = self.credit_bar.get_balance()

        # Run on background thread (using threading.Thread instead of QThread+moveToThread
        # to avoid gRPC/Qt event loop deadlock — gRPC channels interfere with Qt signal delivery
        # when created on a QThread)
        import threading
        self._job_thread = threading.Thread(
            target=self._job_manager.start_job,
            args=(file_list, settings),
            daemon=True,
        )
        self._job_thread.start()

    def _on_file_completed(self, filepath: str, result: dict):
        """Handle per-file completion from JobManager."""
        import os
        filename = os.path.basename(filepath)
        self._results[filename] = result

        if result.get("status") == "success":
            self.gallery.update_file_status(filepath, "completed")
        else:
            self.gallery.update_file_status(filepath, "error")

        # Update inspector if this file is selected
        if hasattr(self, '_selected_file') and self._selected_file == filepath:
            self.inspector.show_file(filepath)

    def _on_progress_updated(self, current: int, total: int, filename: str):
        """Handle progress updates from JobManager."""
        # Switch from indeterminate to determinate on first progress update
        if self.gallery.progress_bar.maximum() == 0:
            self.gallery.progress_bar.setMaximum(100)
            self.status_bar.showMessage(f"กำลังประมวลผล {total} ไฟล์...")
        self.gallery.update_progress(current, total)

    def _on_job_completed(self, summary: dict):
        """Handle job completion from JobManager (finalize already done)."""
        self._is_processing = False
        self._set_processing_state(False)
        self.gallery.reset_progress()
        self._disconnect_job_signals()
        self._cleanup_job_thread()

        successful = summary.get("successful", 0)
        failed = summary.get("failed", 0)
        img_count = summary.get("photo_count", 0)
        vid_count = summary.get("video_count", 0)
        charged = summary.get("charged", 0)
        refunded = summary.get("refunded", 0)
        balance = summary.get("balance", 0)
        csv_files = summary.get("csv_files", [])
        output_folder = summary.get("output_folder", "")

        self.credit_bar.set_balance(balance)
        self.gallery.update_progress(self._process_total, self._process_total)
        self.status_bar.showMessage(
            f"เสร็จสิ้น — สำเร็จ {successful} ไฟล์, ล้มเหลว {failed} ไฟล์"
        )

        # Enable Re-export button after auto-save
        self.inspector.enable_export(True)

        dialog = SummaryDialog(
            successful, failed, img_count, vid_count,
            charged, refunded, balance, csv_files, output_folder, self
        )
        dialog.exec()

    def _on_status_update(self, message: str):
        """Handle step-by-step status updates from JobManager."""
        self.gallery.progress_text.setText(message)
        self.status_bar.showMessage(message)

    def _on_job_failed(self, error_message: str):
        """Handle job failure from JobManager."""
        self._is_processing = False
        self._set_processing_state(False)
        self.gallery.reset_progress()
        self._disconnect_job_signals()
        self._cleanup_job_thread()

        QMessageBox.critical(self, "ประมวลผลล้มเหลว", error_message)
        self.status_bar.showMessage("ประมวลผลล้มเหลว")

    def _disconnect_job_signals(self):
        """Safely disconnect JobManager signals."""
        try:
            self._job_manager.file_completed.disconnect(self._on_file_completed)
            self._job_manager.progress_updated.disconnect(self._on_progress_updated)
            self._job_manager.job_completed.disconnect(self._on_job_completed)
            self._job_manager.job_failed.disconnect(self._on_job_failed)
            self._job_manager.credit_updated.disconnect(self.credit_bar.set_balance)
            self._job_manager.status_update.disconnect(self._on_status_update)
        except RuntimeError:
            pass

    def _cleanup_job_thread(self):
        """Stop job thread cleanly."""
        if self._job_thread:
            if hasattr(self._job_thread, 'quit'):
                # QThread cleanup
                self._job_thread.quit()
                self._job_thread.wait(5000)
            elif hasattr(self._job_thread, 'join'):
                # threading.Thread cleanup
                self._job_thread.join(timeout=5)
            self._job_thread = None

    def _on_stop(self):
        """Stop processing with confirmation."""
        if not self._is_processing:
            return
        reply = QMessageBox.question(
            self, "หยุดประมวลผล",
            "คุณต้องการหยุดประมวลผลใช่หรือไม่?\nไฟล์ที่ยังไม่ได้ประมวลผลจะได้รับเครดิตคืน",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._job_manager.stop_job()
            self._is_processing = False
            self._set_processing_state(False)
            self.gallery.reset_progress()
            self._disconnect_job_signals()
            self._cleanup_job_thread()
            self.status_bar.showMessage("หยุดประมวลผลแล้ว")

    def _on_escape(self):
        if self._is_processing:
            self._on_stop()

    def _set_processing_state(self, is_processing: bool):
        """Lock/unlock all UI components."""
        self.sidebar.set_processing(is_processing)
        self.gallery.set_processing(is_processing)
        self.inspector.set_processing(is_processing)
        self.credit_bar.set_processing(is_processing)

    def _on_file_selected(self, filepath: str):
        self._selected_file = filepath
        self.inspector.show_file(filepath)

    def _on_folder_changed(self, folder_path: str, file_list: list):
        """Update cost estimate when folder changes."""
        self._results.clear()
        self.inspector.clear()
        self.inspector.enable_export(False)
        self._update_cost_estimate()
        self.status_bar.showMessage(
            f"โหลด {len(file_list)} ไฟล์จาก {folder_path}"
        )

    def _on_platform_changed(self, text: str):
        self._update_cost_estimate()
        self._reset_previous_results()

    def _on_keyword_style_changed(self, text: str):
        self._reset_previous_results()

    def _reset_previous_results(self):
        """Reset gallery/inspector when user switches platform or keyword style."""
        if not self._is_processing:
            self._results.clear()
            self.inspector.clear()
            self.gallery.reset_progress()
            self.gallery.reset_file_statuses()

    def _update_cost_estimate(self):
        file_count = self.gallery.get_file_count()
        if file_count > 0:
            rates = self.sidebar.get_platform_rate()  # {"photo": N, "video": N}
            platform = self.sidebar.get_platform_name()
            balance = self.credit_bar.get_balance()
            file_list = self.gallery.get_file_list()
            img_count, vid_count = count_files(file_list)
            self.gallery.update_cost_estimate(
                img_count, vid_count,
                rates["photo"], rates["video"],
                platform, balance,
            )

    def _on_metadata_edited(self, filepath: str, data: dict):
        """Save edited metadata to in-memory results."""
        import os
        filename = os.path.basename(filepath)
        if filename in self._results:
            self._results[filename].update(data)

    def _on_export_csv(self):
        dialog = ExportCsvDialog(self)
        dialog.export_confirmed.connect(self._do_export_csv)
        dialog.exec()

    def _do_export_csv(self):
        """Perform actual CSV re-export with user-chosen directory."""
        from PySide6.QtWidgets import QFileDialog
        from core.data.csv_exporter import CSVExporter

        if not self._results:
            self.status_bar.showMessage("ไม่มีผลลัพธ์ให้ส่งออก")
            return

        # Default to the current gallery folder
        default_dir = self.gallery.get_folder_path() or ""

        # Use manual QFileDialog so we can change the accept button to "Save Here"
        dlg = QFileDialog(self, "Save CSV to folder", default_dir)
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dlg.setLabelText(QFileDialog.DialogLabel.Accept, "Save Here")
        if not dlg.exec():
            return  # User cancelled

        save_dir = dlg.selectedFiles()[0]

        settings = self.sidebar.get_settings()
        platform = settings.get("platform", "iStock")
        model = settings.get("model", "gemini-2.5-pro")
        keyword_style = settings.get("keyword_style", "")

        # Shorten style name for filename (same logic as JobManager)
        if keyword_style.lower().startswith("single"):
            style_tag = "Single"
        elif "hybrid" in keyword_style.lower():
            style_tag = "Hybrid"
        else:
            style_tag = ""

        csv_files = CSVExporter.export_for_platform(
            platform, self._results, save_dir, model, style_tag,
            re_export=True,
        )

        if csv_files:
            names = [os.path.basename(f) for f in csv_files]
            self.status_bar.showMessage(f"ส่งออก CSV ใหม่แล้ว: {', '.join(names)}")
            logger.info(f"Re-export CSV: {csv_files}")
        else:
            self.status_bar.showMessage("ไม่มีผลลัพธ์ที่สำเร็จให้ส่งออก")

    def _on_save_api_key(self, key: str):
        """Save API key to system keyring."""
        save_to_keyring(KEYRING_SERVICE, KEYRING_API_KEY, key)
        self.status_bar.showMessage("บันทึก API key แล้ว")
        logger.info("API key saved to keyring")

    def _on_clear_api_key(self):
        """Clear API key from system keyring."""
        delete_from_keyring(KEYRING_SERVICE, KEYRING_API_KEY)
        self.status_bar.showMessage("ล้าง API key แล้ว")
        logger.info("API key cleared from keyring")

    def _on_rates_loaded(self, rates: dict):
        """Apply server credit rates (photo/video) to config."""
        from core import config
        if rates:
            config.PLATFORM_RATES["iStock"] = {
                "photo": rates.get("istock_photo", 3),
                "video": rates.get("istock_video", 3),
            }
            config.PLATFORM_RATES["Adobe & Shutterstock"] = {
                "photo": rates.get("adobe_photo", 2),
                "video": rates.get("adobe_video", 2),
            }
            config.CREDIT_RATES["iStock"] = config.PLATFORM_RATES["iStock"]
            config.CREDIT_RATES["Adobe"] = {
                "photo": rates.get("adobe_photo", 2),
                "video": rates.get("adobe_video", 2),
            }
            config.CREDIT_RATES["Shutterstock"] = {
                "photo": rates.get("shutterstock_photo", 2),
                "video": rates.get("shutterstock_video", 2),
            }
            logger.info(f"Credit rates updated from server: {config.PLATFORM_RATES}")
            self._update_cost_estimate()

    def _on_refresh_balance(self):
        """Refresh credit balance, promos, and rates from server."""
        try:
            data = api.get_balance_with_promos()
            self.credit_bar.set_balance(data.get("credits", 0))
            self.credit_bar.set_promos(data.get("active_promos", []))
            self._bank_info = data.get("bank_info", {})
            self._on_rates_loaded(data.get("credit_rates", {}))
            self._update_cost_estimate()
            self.status_bar.showMessage("รีเฟรชยอดเรียบร้อย")
        except MaintenanceError as e:
            self._on_maintenance(str(e))
        except NetworkError:
            self.status_bar.showMessage("ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้")
        except APIError as e:
            self.status_bar.showMessage(f"เกิดข้อผิดพลาด: {e}")

    def _on_topup(self):
        promos = self.credit_bar.get_active_promos()
        bank_info = getattr(self, "_bank_info", {})
        dialog = TopUpDialog(self, promos=promos, bank_info=bank_info)
        dialog.exec()

    def _on_history(self):
        """Show credit history from server."""
        try:
            transactions = api.get_history(limit=50)
        except Exception:
            transactions = []
        balance = self.credit_bar.get_balance()
        dialog = HistoryDialog(transactions, balance, self)
        dialog.exec()

    def _on_logout(self):
        reply = QMessageBox.question(
            self, "ออกจากระบบ",
            "คุณต้องการออกจากระบบใช่หรือไม่?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._auth_manager.logout()
            self.status_bar.showMessage("Logged out")
            logger.info("User logged out")
            self.close()
