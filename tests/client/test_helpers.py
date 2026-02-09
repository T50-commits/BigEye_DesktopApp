"""
Tests for client/utils/helpers.py
Covers: is_image, is_video, is_supported_file, scan_folder, count_files,
        format_number, truncate_path.
"""
import os
import pytest
import tempfile

from utils.helpers import (
    is_image, is_video, is_supported_file,
    scan_folder, count_files, format_number, truncate_path,
)


# ═══════════════════════════════════════
# is_image / is_video / is_supported_file
# ═══════════════════════════════════════

class TestFileTypeDetection:

    # ── is_image ──

    @pytest.mark.parametrize("ext", [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"])
    def test_is_image_supported_extensions(self, ext):
        assert is_image(f"/path/to/file{ext}") is True

    @pytest.mark.parametrize("ext", [".mp4", ".mov", ".avi", ".mkv", ".webm"])
    def test_is_image_rejects_video_extensions(self, ext):
        assert is_image(f"/path/to/file{ext}") is False

    def test_is_image_case_insensitive(self):
        assert is_image("/path/to/file.JPG") is True
        assert is_image("/path/to/file.Png") is True

    def test_is_image_unsupported(self):
        assert is_image("/path/to/file.gif") is False
        assert is_image("/path/to/file.txt") is False
        assert is_image("/path/to/file") is False

    # ── is_video ──

    @pytest.mark.parametrize("ext", [".mp4", ".mov", ".avi", ".mkv", ".webm"])
    def test_is_video_supported_extensions(self, ext):
        assert is_video(f"/path/to/file{ext}") is True

    @pytest.mark.parametrize("ext", [".jpg", ".jpeg", ".png"])
    def test_is_video_rejects_image_extensions(self, ext):
        assert is_video(f"/path/to/file{ext}") is False

    def test_is_video_case_insensitive(self):
        assert is_video("/path/to/file.MP4") is True
        assert is_video("/path/to/file.Mov") is True

    # ── is_supported_file ──

    def test_is_supported_file_image(self):
        assert is_supported_file("/path/to/photo.jpg") is True

    def test_is_supported_file_video(self):
        assert is_supported_file("/path/to/clip.mp4") is True

    def test_is_supported_file_unsupported(self):
        assert is_supported_file("/path/to/doc.pdf") is False
        assert is_supported_file("/path/to/readme.txt") is False


# ═══════════════════════════════════════
# scan_folder
# ═══════════════════════════════════════

class TestScanFolder:

    def test_scan_empty_folder(self, tmp_path):
        assert scan_folder(str(tmp_path)) == []

    def test_scan_nonexistent_folder(self):
        assert scan_folder("/nonexistent/path") == []

    def test_scan_none_folder(self):
        assert scan_folder(None) == []

    def test_scan_empty_string(self):
        assert scan_folder("") == []

    def test_scan_finds_supported_files(self, tmp_path):
        # Create test files
        (tmp_path / "photo1.jpg").touch()
        (tmp_path / "photo2.png").touch()
        (tmp_path / "video1.mp4").touch()
        (tmp_path / "readme.txt").touch()
        (tmp_path / "data.csv").touch()

        result = scan_folder(str(tmp_path))
        filenames = [os.path.basename(f) for f in result]
        assert "photo1.jpg" in filenames
        assert "photo2.png" in filenames
        assert "video1.mp4" in filenames
        assert "readme.txt" not in filenames
        assert "data.csv" not in filenames

    def test_scan_returns_absolute_paths(self, tmp_path):
        (tmp_path / "test.jpg").touch()
        result = scan_folder(str(tmp_path))
        assert len(result) == 1
        assert os.path.isabs(result[0])

    def test_scan_returns_sorted(self, tmp_path):
        (tmp_path / "c.jpg").touch()
        (tmp_path / "a.jpg").touch()
        (tmp_path / "b.jpg").touch()
        result = scan_folder(str(tmp_path))
        names = [os.path.basename(f) for f in result]
        assert names == ["a.jpg", "b.jpg", "c.jpg"]

    def test_scan_ignores_subdirectories(self, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "nested.jpg").touch()
        (tmp_path / "top.jpg").touch()
        result = scan_folder(str(tmp_path))
        names = [os.path.basename(f) for f in result]
        assert "top.jpg" in names
        assert "nested.jpg" not in names


# ═══════════════════════════════════════
# count_files
# ═══════════════════════════════════════

class TestCountFiles:

    def test_empty_list(self):
        assert count_files([]) == (0, 0)

    def test_only_images(self):
        files = ["/a/photo1.jpg", "/a/photo2.png", "/a/photo3.tiff"]
        assert count_files(files) == (3, 0)

    def test_only_videos(self):
        files = ["/a/clip1.mp4", "/a/clip2.mov"]
        assert count_files(files) == (0, 2)

    def test_mixed(self):
        files = ["/a/photo.jpg", "/a/clip.mp4", "/a/photo2.png", "/a/clip2.avi"]
        assert count_files(files) == (2, 2)

    def test_unsupported_files_not_counted(self):
        files = ["/a/photo.jpg", "/a/readme.txt", "/a/data.csv"]
        assert count_files(files) == (1, 0)


# ═══════════════════════════════════════
# format_number
# ═══════════════════════════════════════

class TestFormatNumber:

    def test_small_number(self):
        assert format_number(42) == "42"

    def test_thousands(self):
        assert format_number(1000) == "1,000"

    def test_millions(self):
        assert format_number(1234567) == "1,234,567"

    def test_zero(self):
        assert format_number(0) == "0"

    def test_negative(self):
        assert format_number(-1500) == "-1,500"


# ═══════════════════════════════════════
# truncate_path
# ═══════════════════════════════════════

class TestTruncatePath:

    def test_short_path_unchanged(self):
        path = "/Users/test/file.jpg"
        assert truncate_path(path, max_len=40) == path

    def test_long_path_truncated(self):
        path = "/Users/pongtepchithan/Desktop/projects/very/deep/nested/folder/file.jpg"
        result = truncate_path(path, max_len=40)
        assert len(result) < len(path)
        assert "..." in result

    def test_exact_max_len(self):
        path = "x" * 40
        assert truncate_path(path, max_len=40) == path

    def test_very_short_path_with_few_parts(self):
        path = "/a/b"
        assert truncate_path(path, max_len=5) == path  # ≤3 parts → returned as-is
