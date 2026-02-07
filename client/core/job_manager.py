"""
BigEye Pro — Job Manager (Task B-09)
Orchestrates the full processing pipeline:
  reserve → decrypt → cache → process → finalize → CSV → summary → cleanup
"""
import os
import logging
import time

from PySide6.QtCore import QObject, Signal

from core.config import APP_VERSION, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from core.api_client import api, APIError, NetworkError
from core.engines.gemini_engine import GeminiEngine, GeminiError
from core.engines.transcoder import Transcoder
from core.logic.keyword_processor import KeywordProcessor
from core.logic.copyright_guard import CopyrightGuard
from core.data.csv_exporter import CSVExporter
from core.managers.queue_manager import QueueManager
from core.managers.journal_manager import JournalManager
from utils.helpers import is_video, is_image
from utils.security import decrypt_aes

logger = logging.getLogger("bigeye")

CACHE_THRESHOLD = 20  # Create context cache if file count >= this


class JobManager(QObject):
    """Orchestrates the complete job lifecycle."""

    progress_updated = Signal(int, int, str)  # current, total, filename
    file_completed = Signal(str, dict)        # filepath, result
    job_completed = Signal(dict)              # summary
    job_failed = Signal(str)                  # error message
    credit_updated = Signal(int)              # new balance

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = False
        self._job_token = ""
        self._results = {}       # filename → result dict
        self._files = []
        self._settings = {}
        self._engine = GeminiEngine()
        self._queue = QueueManager(self)
        self._keyword_processor = KeywordProcessor()
        self._copyright_guard = CopyrightGuard()
        self._system_prompt = ""
        self._user_prompt = ""
        self._folder_path = ""

        # Connect queue signals
        self._queue.file_completed.connect(self._on_file_completed)
        self._queue.progress_updated.connect(self._on_progress)
        self._queue.all_completed.connect(self._on_all_completed)

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def results(self) -> dict:
        return self._results

    def start_job(self, files: list, settings: dict):
        """
        Start processing job.
        settings keys: api_key, model, platform, platform_rate, keyword_style,
                       max_keywords, title_length, description_length, balance, folder_path
        """
        self._files = files
        self._settings = settings
        self._results = {}
        self._folder_path = settings.get("folder_path", "")

        api_key = settings.get("api_key", "")
        model = settings.get("model", "gemini-2.5-pro")
        platform = settings.get("platform", "iStock")
        rate = settings.get("platform_rate", 3)
        keyword_style = settings.get("keyword_style", "")

        try:
            # ── Step 1: Reserve job with backend ──
            logger.info(f"Reserving job: {len(files)} files, {platform}")
            reserve_data = api.reserve_job(
                file_count=len(files),
                mode=platform,
                keyword_style=keyword_style,
                model=model,
                version=APP_VERSION,
            )
            self._job_token = reserve_data.get("job_token", "")
            encrypted_config = reserve_data.get("config", "")
            concurrency = reserve_data.get("concurrency", {})

            # ── Step 2: Decrypt prompts with AES ──
            if encrypted_config:
                try:
                    config = decrypt_aes(encrypted_config)
                    import json
                    config_data = json.loads(config)
                    self._system_prompt = config_data.get("system_prompt", "")
                    self._user_prompt = config_data.get("user_prompt", "")
                except Exception as e:
                    logger.warning(f"Config decrypt failed, using defaults: {e}")

            # ── Step 3: Download dictionary (if iStock) ──
            blacklist = reserve_data.get("blacklist", [])
            if blacklist:
                self._copyright_guard.initialize(blacklist)
                self._keyword_processor.set_blacklist(set(blacklist))

            # ── Step 4: Set concurrency limits ──
            max_img = concurrency.get("image", 5)
            max_vid = concurrency.get("video", 2)
            self._queue.set_concurrency(max_img, max_vid)

            # ── Step 5: Configure Gemini engine ──
            self._engine.set_api_key(api_key)
            self._engine.set_model(model)

            # ── Step 6: Create context cache if large job ──
            if len(files) >= CACHE_THRESHOLD and self._system_prompt:
                self._engine.create_cache(self._system_prompt)

            # ── Step 7: Create video proxies ──
            # (done lazily inside _process_file)

            # ── Step 8: Create journal ──
            JournalManager.create_journal(
                self._job_token, len(files), platform, rate,
            )

            # ── Step 9: Start processing via QueueManager ──
            self._is_running = True
            self._queue.start_queue(files, self._process_file)

        except NetworkError:
            self.job_failed.emit("Cannot connect to server. Please check your internet.")
        except APIError as e:
            self.job_failed.emit(f"Server error: {e}")
        except Exception as e:
            logger.error(f"Job start failed: {e}")
            self.job_failed.emit(f"Failed to start job: {e}")

    def stop_job(self):
        """Stop the current job gracefully."""
        if not self._is_running:
            return
        logger.info("Stopping job...")
        self._is_running = False
        self._queue.stop()

    # ── File processing (runs on worker thread) ──

    def _process_file(self, filepath: str) -> dict:
        """Process a single file. Called by QueueManager worker threads."""
        filename = os.path.basename(filepath)
        start_time = time.time()

        try:
            prompt = self._user_prompt or f"Generate metadata for this file: {filename}"

            if is_video(filepath):
                # Create proxy for video
                proxy = Transcoder.create_proxy(filepath)
                process_path = proxy if proxy else filepath
                result = self._engine.process_video(process_path, prompt, self._system_prompt)
                # Cleanup proxy
                if proxy:
                    Transcoder.cleanup_proxy(proxy)
            else:
                result = self._engine.process_photo(filepath, prompt, self._system_prompt)

            # Post-process keywords
            keywords = result.get("keywords", [])
            if keywords:
                keywords = self._post_process_keywords(keywords)
                result["keywords"] = keywords

            # Copyright guard scan
            if self._copyright_guard.is_initialized:
                violations = self._copyright_guard.scan_result(result)
                if violations:
                    result["_copyright_violations"] = violations
                    # Auto-clean keywords
                    result["keywords"] = self._copyright_guard.filter_keywords(
                        result.get("keywords", [])
                    )

            result["status"] = "success"
            result["processing_time"] = time.time() - start_time
            return result

        except GeminiError as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": e.error_type.value,
                "processing_time": time.time() - start_time,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": "UNKNOWN",
                "processing_time": time.time() - start_time,
            }

    def _post_process_keywords(self, keywords: list) -> list:
        """Apply keyword processing based on platform/style settings."""
        platform = self._settings.get("platform", "iStock")
        style = self._settings.get("keyword_style", "")
        max_kw = self._settings.get("max_keywords", 45)

        if "istock" in platform.lower():
            return self._keyword_processor.process_istock(keywords, max_kw)
        elif "single" in style.lower():
            return self._keyword_processor.process_single(keywords, max_kw)
        else:
            return self._keyword_processor.process_hybrid(keywords, max_kw)

    # ── Signal handlers ──

    def _on_file_completed(self, filepath: str, result: dict):
        """Handle per-file completion from queue."""
        filename = os.path.basename(filepath)
        self._results[filename] = result

        is_vid = is_video(filepath)
        success = result.get("status") == "success"

        # Update journal
        JournalManager.update_progress(success, is_vid)

        # Emit to UI
        self.file_completed.emit(filepath, result)

    def _on_progress(self, current: int, total: int):
        """Relay progress to UI."""
        self.progress_updated.emit(current, total, "")

    def _on_all_completed(self):
        """Handle job completion: finalize → CSV → sound → cleanup."""
        self._is_running = False

        ok = sum(1 for r in self._results.values() if r.get("status") == "success")
        failed = sum(1 for r in self._results.values() if r.get("status") == "error")
        photos = sum(1 for fn in self._results if is_image(fn))
        videos = sum(1 for fn in self._results if is_video(fn))
        platform = self._settings.get("platform", "iStock")
        model = self._settings.get("model", "gemini-2.5-pro")
        rate = self._settings.get("platform_rate", 3)

        # ── Finalize with backend ──
        refunded = 0
        new_balance = 0
        try:
            fin = api.finalize_job(self._job_token, ok, failed, photos, videos)
            refunded = fin.get("refunded", 0)
            new_balance = fin.get("balance", 0)
            self.credit_updated.emit(new_balance)
        except Exception as e:
            logger.warning(f"Finalize failed: {e}")
            refunded = failed * rate

        # ── Export CSV ──
        csv_files = []
        if ok > 0 and self._folder_path:
            csv_files = CSVExporter.export_for_platform(
                platform, self._results, self._folder_path, model,
            )

        # ── Play completion sound ──
        self._play_sound()

        # ── Cleanup ──
        self._engine.delete_cache()
        self._copyright_guard.clear()
        Transcoder.cleanup_all_proxies()
        JournalManager.delete_journal()

        # ── Build summary ──
        charged = (ok + failed) * rate
        summary = {
            "successful": ok,
            "failed": failed,
            "photo_count": photos,
            "video_count": videos,
            "charged": charged,
            "refunded": refunded,
            "balance": new_balance,
            "csv_files": csv_files,
        }

        logger.info(f"Job complete: {ok} ok, {failed} failed, refunded={refunded}")
        self.job_completed.emit(summary)

    def _play_sound(self):
        """Play completion sound if available."""
        try:
            from core.config import get_asset_path
            sound_path = get_asset_path(os.path.join("assets", "sounds", "complete.wav"))
            if os.path.isfile(sound_path):
                from PySide6.QtMultimedia import QSoundEffect
                from PySide6.QtCore import QUrl
                # Fire-and-forget sound
                effect = QSoundEffect(self)
                effect.setSource(QUrl.fromLocalFile(sound_path))
                effect.play()
        except Exception:
            pass  # Sound is optional
