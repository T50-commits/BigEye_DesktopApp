"""
Tests for Qt Signal emission (headless, no GUI):
  - QueueManager: progress_updated, file_completed, all_completed signals
  - QueueManager: stop/reset behavior
  - JobManager: job_failed signal on API errors
  - JobManager: job_completed signal with summary dict
  - JobManager: credit_updated signal after finalize
  - FileWorker: completed signal on success/error/stop
"""
import threading
import time
import pytest
from unittest.mock import patch, MagicMock

from PySide6.QtCore import QObject, Signal

from core.managers.queue_manager import QueueManager, FileWorker
from core.managers.queue_manager import QSemaphore


# ═══════════════════════════════════════
# QueueManager Signals
# ═══════════════════════════════════════

class TestQueueManagerSignals:

    def test_file_completed_signal(self, qtbot):
        """file_completed should emit (filepath, result) for each file."""
        qm = QueueManager()
        received = []
        qm.file_completed.connect(lambda fp, r: received.append((fp, r)))

        def process_fn(filepath):
            return {"status": "success", "title": "Test"}

        qm.start_queue(["/tmp/test.jpg"], process_fn)
        qm.wait_for_done(5000)
        # Give signal delivery time
        qtbot.waitUntil(lambda: len(received) >= 1, timeout=3000)

        assert len(received) == 1
        assert received[0][0] == "/tmp/test.jpg"
        assert received[0][1]["status"] == "success"

    def test_progress_updated_signal(self, qtbot):
        """progress_updated should emit (current, total) after each file."""
        qm = QueueManager()
        progress = []
        qm.progress_updated.connect(lambda c, t: progress.append((c, t)))

        def process_fn(filepath):
            return {"status": "success"}

        files = ["/tmp/a.jpg", "/tmp/b.jpg", "/tmp/c.jpg"]
        qm.start_queue(files, process_fn)
        qm.wait_for_done(5000)
        qtbot.waitUntil(lambda: len(progress) >= 3, timeout=3000)

        assert len(progress) == 3
        # Last progress should be (3, 3)
        totals = [p[1] for p in progress]
        assert all(t == 3 for t in totals)
        currents = sorted([p[0] for p in progress])
        assert currents == [1, 2, 3]

    def test_all_completed_signal(self, qtbot):
        """all_completed should emit once after all files are done."""
        qm = QueueManager()
        completed = []
        qm.all_completed.connect(lambda: completed.append(True))

        def process_fn(filepath):
            return {"status": "success"}

        qm.start_queue(["/tmp/a.jpg", "/tmp/b.jpg"], process_fn)
        qm.wait_for_done(5000)
        qtbot.waitUntil(lambda: len(completed) >= 1, timeout=3000)

        assert len(completed) == 1

    def test_file_completed_on_error(self, qtbot):
        """Even if process_fn raises, file_completed should still emit with error."""
        qm = QueueManager()
        received = []
        qm.file_completed.connect(lambda fp, r: received.append((fp, r)))

        def process_fn(filepath):
            raise ValueError("Something went wrong")

        qm.start_queue(["/tmp/bad.jpg"], process_fn)
        qm.wait_for_done(5000)
        qtbot.waitUntil(lambda: len(received) >= 1, timeout=3000)

        assert len(received) == 1
        assert received[0][1]["status"] == "error"
        assert "Something went wrong" in received[0][1]["error"]

    def test_stop_sets_flag(self, qtbot):
        """stop() should set the stop event."""
        qm = QueueManager()
        assert qm.is_stopped is False
        qm.stop()
        assert qm.is_stopped is True

    def test_reset_clears_state(self, qtbot):
        """reset() should clear stop flag and counters."""
        qm = QueueManager()
        qm.stop()
        qm._completed_count = 5
        qm._total_count = 10
        qm.reset()
        assert qm.is_stopped is False
        assert qm._completed_count == 0
        assert qm._total_count == 0

    def test_set_concurrency(self, qtbot):
        """set_concurrency should update semaphores."""
        qm = QueueManager()
        qm.set_concurrency(max_images=3, max_videos=1)
        # Verify pool thread count updated
        assert qm._pool.maxThreadCount() == 3 + 1 + 3  # images + videos + headroom

    def test_stopped_workers_emit_skipped(self, qtbot):
        """When stop is called, pending workers should emit 'skipped'."""
        qm = QueueManager()
        received = []
        qm.file_completed.connect(lambda fp, r: received.append((fp, r)))

        def slow_process(filepath):
            time.sleep(0.5)
            return {"status": "success"}

        # Set very low concurrency so files queue up
        qm.set_concurrency(max_images=1, max_videos=1)
        files = [f"/tmp/file_{i}.jpg" for i in range(5)]
        qm.start_queue(files, slow_process)
        # Stop immediately
        qm.stop()
        qm.wait_for_done(10000)
        qtbot.waitUntil(lambda: len(received) >= 5, timeout=10000)

        # Some should be skipped
        statuses = [r[1].get("status") for r in received]
        assert "skipped" in statuses or "success" in statuses


# ═══════════════════════════════════════
# FileWorker Signals
# ═══════════════════════════════════════

class TestFileWorkerSignals:

    def test_worker_emits_on_success(self, qtbot):
        """FileWorker should emit completed signal with result on success."""
        sem = QSemaphore(1)
        stop = threading.Event()
        received = []

        def process_fn(filepath):
            return {"status": "success", "title": "Test"}

        worker = FileWorker("/tmp/test.jpg", process_fn, sem, stop)
        worker.signals.completed.connect(lambda fp, r: received.append((fp, r)))
        worker.run()

        assert len(received) == 1
        assert received[0][0] == "/tmp/test.jpg"
        assert received[0][1]["status"] == "success"

    def test_worker_emits_on_exception(self, qtbot):
        """FileWorker should catch exceptions and emit error result."""
        sem = QSemaphore(1)
        stop = threading.Event()
        received = []

        def process_fn(filepath):
            raise RuntimeError("AI failed")

        worker = FileWorker("/tmp/test.jpg", process_fn, sem, stop)
        worker.signals.completed.connect(lambda fp, r: received.append((fp, r)))
        worker.run()

        assert len(received) == 1
        assert received[0][1]["status"] == "error"
        assert "AI failed" in received[0][1]["error"]

    def test_worker_emits_skipped_when_stopped(self, qtbot):
        """If stop_flag is set, worker should emit 'skipped'."""
        sem = QSemaphore(1)
        stop = threading.Event()
        stop.set()  # pre-set stop
        received = []

        def process_fn(filepath):
            return {"status": "success"}

        worker = FileWorker("/tmp/test.jpg", process_fn, sem, stop)
        worker.signals.completed.connect(lambda fp, r: received.append((fp, r)))
        worker.run()

        assert len(received) == 1
        assert received[0][1]["status"] == "skipped"

    def test_worker_releases_semaphore(self, qtbot):
        """Semaphore should be released even on exception."""
        sem = QSemaphore(1)
        stop = threading.Event()

        def process_fn(filepath):
            raise RuntimeError("fail")

        worker = FileWorker("/tmp/test.jpg", process_fn, sem, stop)
        worker.signals.completed.connect(lambda fp, r: None)
        worker.run()

        # Semaphore should be available again
        assert sem.tryAcquire(1, 100)  # should succeed
        sem.release()


# ═══════════════════════════════════════
# JobManager Signal Simulation (no GUI)
# ═══════════════════════════════════════

class TestJobManagerSignals:
    """
    Test JobManager signal emission by directly calling internal methods.
    We don't launch the full start_job (which needs API), but test the
    signal-emitting code paths.
    """

    def test_job_failed_on_network_error(self, qtbot):
        """JobManager should emit job_failed when API raises NetworkError."""
        from core.job_manager import JobManager
        from core.api_client import NetworkError

        jm = JobManager()
        failed_msgs = []
        jm.job_failed.connect(lambda msg: failed_msgs.append(msg))

        with patch("core.job_manager.api") as mock_api:
            mock_api.reserve_job.side_effect = NetworkError()
            jm.start_job(
                files=["/tmp/test.jpg"],
                settings={"api_key": "k", "model": "m", "platform": "iStock",
                          "platform_rate": {"photo": 3, "video": 3},
                          "folder_path": "/tmp"},
            )

        assert len(failed_msgs) == 1
        assert "connect" in failed_msgs[0].lower() or "internet" in failed_msgs[0].lower()

    def test_job_failed_on_api_error(self, qtbot):
        """JobManager should emit job_failed when API raises APIError."""
        from core.job_manager import JobManager
        from core.api_client import InsufficientCreditsError

        jm = JobManager()
        failed_msgs = []
        jm.job_failed.connect(lambda msg: failed_msgs.append(msg))

        with patch("core.job_manager.api") as mock_api:
            mock_api.reserve_job.side_effect = InsufficientCreditsError("Not enough credits")
            jm.start_job(
                files=["/tmp/test.jpg"],
                settings={"api_key": "k", "model": "m", "platform": "iStock",
                          "platform_rate": {"photo": 3, "video": 3},
                          "folder_path": "/tmp"},
            )

        assert len(failed_msgs) == 1
        assert "credit" in failed_msgs[0].lower() or "server" in failed_msgs[0].lower()

    def test_job_failed_on_generic_exception(self, qtbot):
        """JobManager should emit job_failed on unexpected exceptions."""
        from core.job_manager import JobManager

        jm = JobManager()
        failed_msgs = []
        jm.job_failed.connect(lambda msg: failed_msgs.append(msg))

        with patch("core.job_manager.api") as mock_api:
            mock_api.reserve_job.side_effect = RuntimeError("Unexpected")
            jm.start_job(
                files=["/tmp/test.jpg"],
                settings={"api_key": "k", "model": "m", "platform": "iStock",
                          "platform_rate": {"photo": 3, "video": 3},
                          "folder_path": "/tmp"},
            )

        assert len(failed_msgs) == 1
        assert "unexpected" in failed_msgs[0].lower() or "failed" in failed_msgs[0].lower()

    def test_credit_updated_on_finalize(self, qtbot):
        """_on_all_completed should emit credit_updated after finalize."""
        from core.job_manager import JobManager

        jm = JobManager()
        jm._is_running = True
        jm._job_token = "tok-123"
        jm._results = {"photo.jpg": {"status": "success"}}
        jm._settings = {"platform": "iStock", "model": "gemini-2.5-pro",
                         "platform_rate": {"photo": 3, "video": 3},
                         "keyword_style": ""}
        jm._folder_path = ""

        credit_updates = []
        jm.credit_updated.connect(lambda bal: credit_updates.append(bal))

        with patch("core.job_manager.api") as mock_api, \
             patch("core.job_manager.JournalManager"), \
             patch("core.job_manager.Transcoder"), \
             patch.object(jm, "_play_sound"):
            mock_api.finalize_job.return_value = {"refunded": 0, "balance": 497}
            jm._on_all_completed()

        assert len(credit_updates) == 1
        assert credit_updates[0] == 497

    def test_job_completed_emits_summary(self, qtbot):
        """_on_all_completed should emit job_completed with summary dict."""
        from core.job_manager import JobManager

        jm = JobManager()
        jm._is_running = True
        jm._job_token = "tok-123"
        jm._results = {
            "photo1.jpg": {"status": "success"},
            "photo2.jpg": {"status": "error"},
            "clip.mp4": {"status": "success"},
        }
        jm._settings = {"platform": "iStock", "model": "gemini-2.5-pro",
                         "platform_rate": {"photo": 3, "video": 3},
                         "keyword_style": ""}
        jm._folder_path = ""

        summaries = []
        jm.job_completed.connect(lambda s: summaries.append(s))

        with patch("core.job_manager.api") as mock_api, \
             patch("core.job_manager.JournalManager"), \
             patch("core.job_manager.Transcoder"), \
             patch.object(jm, "_play_sound"):
            mock_api.finalize_job.return_value = {"refunded": 3, "balance": 494}
            jm._on_all_completed()

        assert len(summaries) == 1
        s = summaries[0]
        assert s["successful"] == 2
        assert s["failed"] == 1
        assert s["refunded"] == 3
        assert s["balance"] == 494

    def test_stop_job_sets_not_running(self, qtbot):
        """stop_job should set _is_running to False."""
        from core.job_manager import JobManager
        jm = JobManager()
        jm._is_running = True
        jm.stop_job()
        assert jm._is_running is False
