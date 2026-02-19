"""
BigEye Pro — Job Manager (Task B-09)
Orchestrates the full processing pipeline:
  reserve → decrypt → cache → process → finalize → CSV → summary → cleanup
"""
import os
import shutil
import logging
import time
import threading

from PySide6.QtCore import QObject, Signal

from core.config import APP_VERSION, AES_KEY_HEX, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from core.api_client import api, APIError, NetworkError, MaintenanceError
from core.engines.gemini_engine import GeminiEngine, GeminiError, GeminiErrorType
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
    status_update = Signal(str)              # step description for UI

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
        self._prompt_template = ""  # raw prompt with {placeholders}
        self._dictionary = ""       # keyword dictionary for iStock
        self._folder_path = ""
        self._video_queue = []       # ordered list of video filepaths for pipeline
        self._video_index = 0        # next video to prefetch
        self._prefetch_lock = threading.Lock()

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
        rates = settings.get("platform_rate", {"photo": 3, "video": 3})
        if isinstance(rates, int):
            rates = {"photo": rates, "video": rates}
        keyword_style = settings.get("keyword_style", "")

        # Count photos and videos
        from utils.helpers import count_files
        img_count, vid_count = count_files(files)

        try:
            # ── Step 1: Reserve job with backend ──
            self.status_update.emit("Checking credits...")
            logger.info(f"Reserving job: {len(files)} files ({img_count}p+{vid_count}v), {platform}")
            reserve_data = api.reserve_job(
                file_count=len(files),
                mode=platform,
                keyword_style=keyword_style,
                model=model,
                version=APP_VERSION,
                photo_count=img_count,
                video_count=vid_count,
            )
            self._job_token = reserve_data.get("job_token", "")
            encrypted_config = reserve_data.get("config", "")
            concurrency = reserve_data.get("concurrency", {})

            self.status_update.emit("Preparing files...")

            # ── Step 2: Decrypt prompt with AES ──
            if encrypted_config:
                try:
                    self._prompt_template = decrypt_aes(encrypted_config, AES_KEY_HEX)
                    pass
                except Exception as e:
                    logger.warning(f"Config decrypt failed: {e}")
                    self._prompt_template = ""

            # ── Step 3: Store dictionary + blacklist ──
            self._dictionary = reserve_data.get("dictionary", "")
            if self._dictionary:
                pass

            blacklist = reserve_data.get("blacklist", [])
            if blacklist:
                self._copyright_guard.initialize(blacklist)
                self._keyword_processor.set_blacklist(set(blacklist))

            self.status_update.emit("Setting up engine...")

            # ── Step 4: Set concurrency limits ──
            max_img = concurrency.get("image", 5)
            max_vid = concurrency.get("video", 2)
            self._queue.set_concurrency(max_img, max_vid)

            # ── Step 5: Configure Gemini engine ──
            self._engine.set_api_key(api_key)
            self._engine.set_model(model)

            # ลบไฟล์เก่าที่ค้างใน Gemini (ครั้งเดียวตอนเริ่ม job)
            self.status_update.emit("กำลังเตรียมระบบ...")
            self._engine.cleanup_all_remote_files()

            # ── Step 6: Create context cache if large job ──
            cache_threshold = reserve_data.get("cache_threshold", CACHE_THRESHOLD)
            if self._prompt_template:
                # Always store system_prompt for inline system_instruction fallback
                self._engine.set_system_prompt(self._prompt_template)
                if len(files) >= cache_threshold:
                    self.status_update.emit("Optimizing batch...")
                    self._engine.create_cache(self._prompt_template)

            # ── Step 7: Create video proxies ──
            # (done lazily inside _process_file)

            # ── Step 8: Create journal ──
            # Use photo_rate from server response, fallback to config
            journal_rate = reserve_data.get("photo_rate", rates.get("photo", 3))
            JournalManager.create_journal(
                self._job_token, len(files), platform, journal_rate,
            )

            # ── Step 9: Build video pipeline queue ──
            self._video_queue = [f for f in files if is_video(f)]
            self._video_index = 0

            # Pre-upload first video proxy while images start processing
            if self._video_queue:
                first_vid = self._video_queue[0]
                proxy = Transcoder.create_proxy(first_vid)
                prefetch_path = proxy if proxy else first_vid
                threading.Thread(
                    target=self._engine.prefetch_video,
                    args=(prefetch_path,),
                    daemon=True,
                ).start()
                self._video_index = 1

            # ── Step 10: Start processing via QueueManager ──
            self.status_update.emit("Processing...")
            self._is_running = True
            self._queue.start_queue(files, self._process_file)

        except MaintenanceError as e:
            self.job_failed.emit("ระบบปิดปรับปรุงชั่วคราว กรุณาลองใหม่ภายหลัง")
        except NetworkError:
            self.job_failed.emit("ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาตรวจสอบอินเทอร์เน็ต")
        except APIError as e:
            self.job_failed.emit(str(e))
        except Exception as e:
            logger.error(f"Job start failed: {e}")
            self.job_failed.emit(f"ไม่สามารถเริ่มประมวลผลได้: {e}")

    def stop_job(self):
        """Stop the current job gracefully."""
        if not self._is_running:
            return
        logger.info("Stopping job...")
        self._is_running = False
        self._queue.stop()

    # ── File processing (runs on worker thread) ──

    def _build_prompt(self, filepath: str) -> str:
        """Build the final prompt by filling in placeholders."""
        is_vid = is_video(filepath)
        media_type = "video" if is_vid else "image"
        max_kw = self._settings.get("max_keywords", 45)
        title_limit = self._settings.get("title_length", 70)
        desc_limit = self._settings.get("description_length", 200)

        # บอก AI ให้ใช้ limit เล็กกว่าจริง 10% เพื่อชดเชยการนับตัวอักษรผิดของ AI
        title_limit_for_ai = int(title_limit * 0.90)
        desc_limit_for_ai  = int(desc_limit  * 0.90)
        title_min_for_ai   = int(title_limit * 0.65)
        desc_min_for_ai    = int(desc_limit  * 0.65)

        # Video-specific instruction
        video_instruction = ""
        if is_vid:
            video_instruction = (
                "For video: Also provide 'poster_timecode' (best frame as HH:MM:SS:FF) "
                "and 'shot_speed' (one of: Real Time, Slow Motion, Time Lapse)."
            )

        prompt = self._prompt_template
        prompt = prompt.replace("{media_type_str}", media_type)
        prompt = prompt.replace("{keyword_count}", str(max_kw + 10))  # overfetch
        prompt = prompt.replace("{title_min}", str(title_min_for_ai))
        prompt = prompt.replace("{title_limit}", str(title_limit_for_ai))
        prompt = prompt.replace("{desc_min}", str(desc_min_for_ai))
        prompt = prompt.replace("{desc_limit}", str(desc_limit_for_ai))
        prompt = prompt.replace("{video_instruction}", video_instruction)

        # Insert dictionary for iStock mode
        if "{keyword_data}" in prompt:
            prompt = prompt.replace("{keyword_data}", self._dictionary)

        return prompt

    def _process_file(self, filepath: str) -> dict:
        """Process a single file. Called by QueueManager worker threads."""
        filename = os.path.basename(filepath)
        start_time = time.time()

        try:
            # Build prompt with placeholders filled
            if self._prompt_template:
                prompt = self._build_prompt(filepath)
            else:
                prompt = f"Analyze this {'video' if is_video(filepath) else 'image'} and generate stock metadata in JSON with keys: title, description, keywords."

            if is_video(filepath):
                # Create proxy for video
                self.status_update.emit(f"Uploading / Processing: {filename}")
                proxy = Transcoder.create_proxy(filepath)
                process_path = proxy if proxy else filepath

                # Pipeline: prefetch next video while this one generates
                self._prefetch_next_video()

                result = self._engine.process_video(process_path, prompt)
                # Cleanup proxy
                if proxy:
                    Transcoder.cleanup_proxy(proxy)
            else:
                result = self._engine.process_photo(filepath, prompt)

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
            if e.error_type == GeminiErrorType.RATE_LIMIT:
                user_msg = "ส่งงานเร็วเกินไป กรุณารอสักครู่แล้วลองใหม่"
            elif e.error_type == GeminiErrorType.SAFETY:
                user_msg = "เนื้อหาไม่ผ่านตัวกรองความปลอดภัย"
            elif e.error_type == GeminiErrorType.TIMEOUT:
                user_msg = "ประมวลผลนานเกินไป กรุณาลองใหม่"
            elif e.error_type == GeminiErrorType.CONTENT_TOO_LARGE:
                user_msg = "ไฟล์ใหญ่เกินไป กรุณาลดขนาดวิดีโอ"
            elif e.error_type == GeminiErrorType.INVALID_KEY:
                user_msg = "API Key ไม่ถูกต้อง กรุณาตรวจสอบ"
            elif e.error_type == GeminiErrorType.MODEL_NOT_FOUND:
                user_msg = "ไม่พบ Model ที่เลือก กรุณาเปลี่ยน Model"
            elif e.error_type == GeminiErrorType.QUOTA:
                user_msg = "Quota หมด กรุณาตรวจสอบ API Key"
            else:
                user_msg = "ไม่สามารถประมวลผลได้ กรุณาลองใหม่"
            return {
                "status": "error",
                "error": user_msg,
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

    def _prefetch_next_video(self):
        """Pre-upload the next video proxy in background while current video generates."""
        with self._prefetch_lock:
            if self._video_index >= len(self._video_queue):
                return
            # จำกัด prefetch ไม่เกิน 2 ไฟล์ค้างใน Gemini
            if len(self._engine._prefetched) >= 2:
                return
            next_vid = self._video_queue[self._video_index]
            self._video_index += 1

        def _do_prefetch():
            try:
                proxy = Transcoder.create_proxy(next_vid)
                prefetch_path = proxy if proxy else next_vid
                self._engine.prefetch_video(prefetch_path)
            except Exception as e:
                logger.warning(f"Prefetch thread error: {e}")

        threading.Thread(target=_do_prefetch, daemon=True).start()

    def _post_process_keywords(self, keywords: list) -> list:
        """Apply keyword processing based on platform/style settings."""
        platform = self._settings.get("platform", "iStock")
        style = self._settings.get("keyword_style", "")
        max_kw = self._settings.get("max_keywords", 45)

        if "istock" in platform.lower():
            return self._keyword_processor.process_istock(keywords, max_kw)
        elif style.lower().startswith("single"):
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
        rates = self._settings.get("platform_rate", {"photo": 3, "video": 3})
        if isinstance(rates, int):
            rates = {"photo": rates, "video": rates}

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
            # Estimate refund locally as fallback
            refunded = (failed * rates.get("photo", 3))

        # ── Export CSV ──
        csv_files = []
        if ok > 0 and self._folder_path:
            keyword_style = self._settings.get("keyword_style", "")
            # Shorten style name for filename
            if keyword_style.lower().startswith("single"):
                style_tag = "Single"
            elif "hybrid" in keyword_style.lower():
                style_tag = "Hybrid"
            else:
                style_tag = ""
            csv_files = CSVExporter.export_for_platform(
                platform, self._results, self._folder_path, model, style_tag,
            )

        # ── Move completed files to output folder ──
        output_folder = ""
        if ok > 0 and self._folder_path:
            output_folder = self._move_completed_files(csv_files)

        # ── Play completion sound ──
        self._play_sound()

        # ── Cleanup ──
        self._engine.cleanup_prefetched()
        self._engine.delete_cache()
        self._copyright_guard.clear()
        Transcoder.cleanup_all_proxies()
        JournalManager.delete_journal()

        # ── Build summary ──
        charged = (ok * rates.get("photo", 3)) + (videos * rates.get("video", 3))
        summary = {
            "successful": ok,
            "failed": failed,
            "photo_count": photos,
            "video_count": videos,
            "charged": charged,
            "refunded": refunded,
            "balance": new_balance,
            "csv_files": csv_files,
            "output_folder": output_folder,
        }

        logger.info(f"Job complete: {ok} ok, {failed} failed, refunded={refunded}")
        self.job_completed.emit(summary)

    def _move_completed_files(self, csv_files: list) -> str:
        """สร้างโฟลเดอร์ output และย้ายไฟล์ที่สำเร็จ + CSV ไปไว้ใน folder นั้น
        Returns: path ของ output folder (หรือ "" ถ้าล้มเหลว)
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = os.path.basename(self._folder_path.rstrip("/\\"))
        output_dir = os.path.join(self._folder_path, f"BigEye_Output_{timestamp}")
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            logger.warning(f"Cannot create output folder: {e}")
            return ""

        # ย้ายไฟล์ที่ประมวลผลสำเร็จ
        moved = 0
        for filepath in self._files:
            filename = os.path.basename(filepath)
            if self._results.get(filename, {}).get("status") == "success":
                dest = os.path.join(output_dir, filename)
                try:
                    shutil.move(filepath, dest)
                    moved += 1
                except Exception as e:
                    logger.warning(f"Cannot move {filename}: {e}")

        # ย้าย CSV ไปด้วย
        for csv_path in csv_files:
            if os.path.isfile(csv_path):
                try:
                    shutil.move(csv_path, os.path.join(output_dir, os.path.basename(csv_path)))
                except Exception as e:
                    logger.warning(f"Cannot move CSV {os.path.basename(csv_path)}: {e}")

        logger.info(f"Moved {moved} files + {len(csv_files)} CSV(s) → {output_dir}")
        return output_dir

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
