"""
Tests for client/core/managers/journal_manager.py
Covers: create_journal, update_progress, read_journal, delete_journal, recover_on_startup.
"""
import json
import os
import pytest
from unittest.mock import patch, MagicMock

from core.managers.journal_manager import JournalManager


@pytest.fixture
def journal_path(tmp_path):
    """Override RECOVERY_PATH to use a temp directory."""
    path = str(tmp_path / "recovery.json")
    with patch("core.managers.journal_manager.RECOVERY_PATH", path):
        yield path


# ═══════════════════════════════════════
# create_journal
# ═══════════════════════════════════════

class TestCreateJournal:

    def test_creates_file(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            JournalManager.create_journal("token-123", 10, "iStock", 3)
            assert os.path.isfile(journal_path)

    def test_correct_content(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            JournalManager.create_journal("token-abc", 5, "Adobe & Shutterstock", 2)
            with open(journal_path, "r") as f:
                data = json.load(f)
            assert data["job_token"] == "token-abc"
            assert data["file_count"] == 5
            assert data["mode"] == "Adobe & Shutterstock"
            assert data["credit_rate"] == 2
            assert data["success_count"] == 0
            assert data["failed_count"] == 0
            assert data["photo_count"] == 0
            assert data["video_count"] == 0


# ═══════════════════════════════════════
# update_progress
# ═══════════════════════════════════════

class TestUpdateProgress:

    def test_increment_success_photo(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            JournalManager.create_journal("token-1", 10, "iStock", 3)
            JournalManager.update_progress(success=True, is_video=False)
            data = JournalManager.read_journal()
            assert data["success_count"] == 1
            assert data["photo_count"] == 1

    def test_increment_failed_video(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            JournalManager.create_journal("token-1", 10, "iStock", 3)
            JournalManager.update_progress(success=False, is_video=True)
            data = JournalManager.read_journal()
            assert data["failed_count"] == 1
            assert data["video_count"] == 1

    def test_multiple_updates(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            JournalManager.create_journal("token-1", 10, "iStock", 3)
            JournalManager.update_progress(True, False)   # success photo
            JournalManager.update_progress(True, True)    # success video
            JournalManager.update_progress(False, False)  # failed photo
            data = JournalManager.read_journal()
            assert data["success_count"] == 2
            assert data["failed_count"] == 1
            assert data["photo_count"] == 2
            assert data["video_count"] == 1

    def test_update_without_journal_does_nothing(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            # No journal created — should not raise
            JournalManager.update_progress(True, False)


# ═══════════════════════════════════════
# read_journal
# ═══════════════════════════════════════

class TestReadJournal:

    def test_read_existing(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            JournalManager.create_journal("token-1", 5, "iStock", 3)
            data = JournalManager.read_journal()
            assert data is not None
            assert data["job_token"] == "token-1"

    def test_read_nonexistent(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            assert JournalManager.read_journal() is None

    def test_read_corrupted_json(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            with open(journal_path, "w") as f:
                f.write("not valid json{{{")
            assert JournalManager.read_journal() is None


# ═══════════════════════════════════════
# delete_journal
# ═══════════════════════════════════════

class TestDeleteJournal:

    def test_delete_existing(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            JournalManager.create_journal("token-1", 5, "iStock", 3)
            assert os.path.isfile(journal_path)
            JournalManager.delete_journal()
            assert not os.path.isfile(journal_path)

    def test_delete_nonexistent(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            JournalManager.delete_journal()  # Should not raise


# ═══════════════════════════════════════
# recover_on_startup
# ═══════════════════════════════════════

class TestRecoverOnStartup:

    def test_no_journal_returns_none(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            assert JournalManager.recover_on_startup() is None

    def test_recovery_with_api_client(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            JournalManager.create_journal("token-1", 10, "iStock", 3)
            JournalManager.update_progress(True, False)   # 1 success photo
            JournalManager.update_progress(False, False)  # 1 failed photo

            mock_api = MagicMock()
            mock_api.finalize_job.return_value = {"refunded": 24}

            info = JournalManager.recover_on_startup(api_client=mock_api)
            assert info is not None
            assert info["platform"] == "iStock"
            assert info["total_files"] == 10
            assert info["ok_count"] == 1
            assert info["failed_count"] == 1
            assert info["refunded"] == 24
            # Journal should be deleted after recovery
            assert not os.path.isfile(journal_path)

    def test_recovery_api_failure_estimates_refund(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            JournalManager.create_journal("token-1", 10, "iStock", 3)
            JournalManager.update_progress(True, False)   # 1 success
            JournalManager.update_progress(False, False)  # 1 failed

            mock_api = MagicMock()
            mock_api.finalize_job.side_effect = Exception("Network error")

            info = JournalManager.recover_on_startup(api_client=mock_api)
            # Estimated: unprocessed=8, failed=1 → (8+1)*3 = 27
            assert info["refunded"] == 27

    def test_recovery_without_api_client(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            JournalManager.create_journal("token-1", 10, "iStock", 3)
            info = JournalManager.recover_on_startup(api_client=None)
            assert info is not None
            assert info["refunded"] == 0  # No API → no finalize → 0 refund

    def test_recovery_info_fields(self, journal_path):
        with patch("core.managers.journal_manager.RECOVERY_PATH", journal_path):
            JournalManager.create_journal("token-1", 10, "iStock", 3)
            info = JournalManager.recover_on_startup()
            assert "platform" in info
            assert "total_files" in info
            assert "completed" in info
            assert "ok_count" in info
            assert "failed_count" in info
            assert "credits_reserved" in info
            assert "refunded" in info
            assert info["credits_reserved"] == 30  # 10 * 3
