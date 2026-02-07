"""
BigEye Pro — Journal Manager (Task B-09)
Handles crash recovery via recovery.json journal file.
On startup: detects unfinished jobs → finalizes with backend → refunds unused credits.
"""
import json
import os
import logging

from core.config import RECOVERY_PATH

logger = logging.getLogger("bigeye")


class JournalManager:
    """Manages recovery journal for crash recovery."""

    @staticmethod
    def create_journal(job_token: str, file_count: int, mode: str, credit_rate: int):
        """Create a new recovery journal at start of job."""
        data = {
            "job_token": job_token,
            "file_count": file_count,
            "mode": mode,
            "credit_rate": credit_rate,
            "success_count": 0,
            "failed_count": 0,
            "photo_count": 0,
            "video_count": 0,
        }
        os.makedirs(os.path.dirname(RECOVERY_PATH), exist_ok=True)
        with open(RECOVERY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Journal created: {job_token}, {file_count} files, {mode}")

    @staticmethod
    def update_progress(success: bool, is_video: bool):
        """Update journal with per-file progress."""
        journal = JournalManager.read_journal()
        if not journal:
            return
        if success:
            journal["success_count"] += 1
        else:
            journal["failed_count"] += 1
        if is_video:
            journal["video_count"] += 1
        else:
            journal["photo_count"] += 1
        try:
            with open(RECOVERY_PATH, "w", encoding="utf-8") as f:
                json.dump(journal, f, indent=2)
        except OSError as e:
            logger.warning(f"Journal update failed: {e}")

    @staticmethod
    def read_journal() -> dict | None:
        """Read existing recovery journal."""
        if not os.path.isfile(RECOVERY_PATH):
            return None
        try:
            with open(RECOVERY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def delete_journal():
        """Delete the recovery journal."""
        try:
            if os.path.isfile(RECOVERY_PATH):
                os.remove(RECOVERY_PATH)
                logger.info("Journal deleted")
        except OSError as e:
            logger.warning(f"Journal delete failed: {e}")

    @staticmethod
    def recover_on_startup(api_client=None) -> dict | None:
        """
        Check for unfinished job on startup.
        If found, finalize with backend and return recovery info (ENGLISH).
        """
        journal = JournalManager.read_journal()
        if not journal:
            return None

        job_token = journal.get("job_token", "")
        ok = journal.get("success_count", 0)
        failed = journal.get("failed_count", 0)
        photos = journal.get("photo_count", 0)
        videos = journal.get("video_count", 0)
        total = journal.get("file_count", 0)
        rate = journal.get("credit_rate", 3)

        refunded = 0

        # Finalize with backend to get refund
        if api_client and job_token:
            try:
                result = api_client.finalize_job(job_token, ok, failed, photos, videos)
                refunded = result.get("refunded", 0)
                logger.info(f"Recovery finalized: refunded={refunded}")
            except Exception as e:
                logger.warning(f"Recovery finalize failed: {e}")
                # Estimate refund: unprocessed files * rate
                unprocessed = total - ok - failed
                refunded = (unprocessed + failed) * rate

        recovery_info = {
            "platform": journal.get("mode", "Unknown"),
            "total_files": total,
            "completed": ok + failed,
            "ok_count": ok,
            "failed_count": failed,
            "credits_reserved": total * rate,
            "refunded": refunded,
        }

        JournalManager.delete_journal()
        return recovery_info
