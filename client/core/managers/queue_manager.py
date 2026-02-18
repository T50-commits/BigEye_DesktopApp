"""
BigEye Pro — Queue Manager (Task B-09)
Manages concurrent file processing using QThreadPool with QSemaphore.
Image: max 5 concurrent, Video: max 2 concurrent.
"""
import os
import logging
import threading
from typing import Callable, Optional

from PySide6.QtCore import QObject, Signal, QThreadPool, QSemaphore, QRunnable, Slot

from utils.helpers import is_video

logger = logging.getLogger("bigeye")


class FileWorker(QRunnable):
    """Processes a single file on a thread pool thread."""

    class Signals(QObject):
        completed = Signal(str, dict)  # filepath, result_or_error

    def __init__(self, filepath: str, process_fn: Callable,
                 semaphore: QSemaphore, stop_flag: threading.Event):
        super().__init__()
        self.filepath = filepath
        self._process_fn = process_fn
        self._semaphore = semaphore
        self._stop_flag = stop_flag
        self.signals = self.Signals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        # Acquire semaphore (blocks until slot available)
        self._semaphore.acquire()
        try:
            if self._stop_flag.is_set():
                self.signals.completed.emit(self.filepath, {
                    "status": "skipped", "error": "Job stopped",
                })
                return

            result = self._process_fn(self.filepath)
            self.signals.completed.emit(self.filepath, result)

        except Exception as e:
            logger.error(f"Worker error {os.path.basename(self.filepath)}: {e}")
            self.signals.completed.emit(self.filepath, {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
            })
        finally:
            self._semaphore.release()


class QueueManager(QObject):
    """Manages concurrent processing of image and video files."""

    progress_updated = Signal(int, int)  # current, total
    file_completed = Signal(str, dict)   # filepath, result
    all_completed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(10)  # 5 image + 3 video + headroom
        self._image_semaphore = QSemaphore(5)
        self._video_semaphore = QSemaphore(3)
        self._stop_event = threading.Event()
        self._completed_count = 0
        self._total_count = 0
        self._lock = threading.Lock()

    def set_concurrency(self, max_images: int = 5, max_videos: int = 3):
        """Set concurrency limits from server config."""
        self._image_semaphore = QSemaphore(max_images)
        self._video_semaphore = QSemaphore(max_videos)
        self._pool.setMaxThreadCount(max_images + max_videos + 3)

    def start_queue(self, files: list, process_fn: Callable):
        """
        Queue all files for processing.
        process_fn(filepath) → dict with result or raises exception.
        """
        self._stop_event.clear()
        self._completed_count = 0
        self._total_count = len(files)

        logger.info(f"Queue started: {self._total_count} files")

        for filepath in files:
            if self._stop_event.is_set():
                break

            sem = self._video_semaphore if is_video(filepath) else self._image_semaphore
            worker = FileWorker(filepath, process_fn, sem, self._stop_event)
            worker.signals.completed.connect(self._on_file_completed)
            self._pool.start(worker)

    def _on_file_completed(self, filepath: str, result: dict):
        """Handle completion of a single file."""
        with self._lock:
            self._completed_count += 1
            current = self._completed_count
            total = self._total_count

        self.file_completed.emit(filepath, result)
        self.progress_updated.emit(current, total)

        if current >= total:
            self.all_completed.emit()
            logger.info(f"Queue complete: {total} files processed")

    def stop(self):
        """Signal all workers to stop."""
        self._stop_event.set()
        logger.info("Queue stop requested")

    def reset(self):
        """Reset for new job."""
        self._stop_event.clear()
        self._completed_count = 0
        self._total_count = 0

    def wait_for_done(self, timeout_ms: int = 30000) -> bool:
        """Wait for all queued tasks to finish. Returns True if all done."""
        return self._pool.waitForDone(timeout_ms)

    @property
    def is_stopped(self) -> bool:
        return self._stop_event.is_set()
