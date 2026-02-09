"""
Tests for file processing logic:
  - utils/helpers.py: is_image, is_video, is_supported_file, scan_folder, count_files
  - File type detection across all supported extensions
  - Folder scanning with mixed file types
"""
import os
import pytest

from utils.helpers import (
    is_image, is_video, is_supported_file,
    scan_folder, count_files, format_number, truncate_path,
)
from core.config import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, ALL_EXTENSIONS


# ═══════════════════════════════════════
# File Type Detection
# ═══════════════════════════════════════

class TestIsImage:

    @pytest.mark.parametrize("ext", sorted(IMAGE_EXTENSIONS))
    def test_all_image_extensions(self, ext):
        assert is_image(f"photo{ext}") is True

    @pytest.mark.parametrize("ext", sorted(VIDEO_EXTENSIONS))
    def test_video_not_image(self, ext):
        assert is_image(f"clip{ext}") is False

    def test_case_insensitive(self):
        assert is_image("photo.JPG") is True
        assert is_image("photo.Jpeg") is True
        assert is_image("photo.PNG") is True

    def test_unsupported_extension(self):
        assert is_image("file.txt") is False
        assert is_image("file.pdf") is False
        assert is_image("file.psd") is False

    def test_no_extension(self):
        assert is_image("noext") is False

    def test_hidden_file(self):
        assert is_image(".hidden.jpg") is True

    def test_full_path(self):
        assert is_image("/Users/test/photos/sunset.jpg") is True
        assert is_image("C:\\Users\\test\\photos\\sunset.png") is True


class TestIsVideo:

    @pytest.mark.parametrize("ext", sorted(VIDEO_EXTENSIONS))
    def test_all_video_extensions(self, ext):
        assert is_video(f"clip{ext}") is True

    @pytest.mark.parametrize("ext", sorted(IMAGE_EXTENSIONS))
    def test_image_not_video(self, ext):
        assert is_video(f"photo{ext}") is False

    def test_case_insensitive(self):
        assert is_video("clip.MP4") is True
        assert is_video("clip.Mov") is True

    def test_unsupported(self):
        assert is_video("file.flv") is False
        assert is_video("file.wmv") is False


class TestIsSupportedFile:

    @pytest.mark.parametrize("ext", sorted(ALL_EXTENSIONS))
    def test_all_supported(self, ext):
        assert is_supported_file(f"file{ext}") is True

    def test_unsupported(self):
        assert is_supported_file("file.txt") is False
        assert is_supported_file("file.doc") is False
        assert is_supported_file("file.exe") is False


# ═══════════════════════════════════════
# Folder Scanning
# ═══════════════════════════════════════

class TestScanFolder:

    def test_scan_with_mixed_files(self, tmp_path):
        """Only supported media files should be returned."""
        (tmp_path / "photo.jpg").write_bytes(b"\xff\xd8")
        (tmp_path / "clip.mp4").write_bytes(b"\x00")
        (tmp_path / "readme.txt").write_text("ignore me")
        (tmp_path / "data.csv").write_text("a,b,c")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")

        files = scan_folder(str(tmp_path))
        basenames = [os.path.basename(f) for f in files]
        assert "photo.jpg" in basenames
        assert "clip.mp4" in basenames
        assert "image.png" in basenames
        assert "readme.txt" not in basenames
        assert "data.csv" not in basenames

    def test_scan_returns_absolute_paths(self, tmp_path):
        (tmp_path / "test.jpg").write_bytes(b"\xff")
        files = scan_folder(str(tmp_path))
        assert all(os.path.isabs(f) for f in files)

    def test_scan_sorted_alphabetically(self, tmp_path):
        for name in ["c.jpg", "a.jpg", "b.jpg"]:
            (tmp_path / name).write_bytes(b"\xff")
        files = scan_folder(str(tmp_path))
        basenames = [os.path.basename(f) for f in files]
        assert basenames == ["a.jpg", "b.jpg", "c.jpg"]

    def test_scan_empty_folder(self, tmp_path):
        assert scan_folder(str(tmp_path)) == []

    def test_scan_nonexistent_folder(self):
        assert scan_folder("/nonexistent/path") == []

    def test_scan_none_path(self):
        assert scan_folder(None) == []

    def test_scan_empty_string(self):
        assert scan_folder("") == []

    def test_scan_ignores_subdirectories(self, tmp_path):
        (tmp_path / "photo.jpg").write_bytes(b"\xff")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.jpg").write_bytes(b"\xff")
        files = scan_folder(str(tmp_path))
        basenames = [os.path.basename(f) for f in files]
        assert "photo.jpg" in basenames
        assert "nested.jpg" not in basenames  # not recursive

    def test_scan_case_insensitive_extensions(self, tmp_path):
        (tmp_path / "photo.JPG").write_bytes(b"\xff")
        (tmp_path / "clip.MP4").write_bytes(b"\x00")
        files = scan_folder(str(tmp_path))
        assert len(files) == 2


# ═══════════════════════════════════════
# Count Files
# ═══════════════════════════════════════

class TestCountFiles:

    def test_count_mixed(self):
        files = ["a.jpg", "b.png", "c.mp4", "d.mov", "e.tiff"]
        imgs, vids = count_files(files)
        assert imgs == 3  # jpg, png, tiff
        assert vids == 2  # mp4, mov

    def test_count_all_images(self):
        files = ["a.jpg", "b.png", "c.jpeg"]
        imgs, vids = count_files(files)
        assert imgs == 3
        assert vids == 0

    def test_count_all_videos(self):
        files = ["a.mp4", "b.mov", "c.avi"]
        imgs, vids = count_files(files)
        assert imgs == 0
        assert vids == 3

    def test_count_empty(self):
        assert count_files([]) == (0, 0)

    def test_count_unsupported_ignored(self):
        files = ["a.txt", "b.pdf"]
        assert count_files(files) == (0, 0)


# ═══════════════════════════════════════
# Format Number
# ═══════════════════════════════════════

class TestFormatNumber:

    def test_small_number(self):
        assert format_number(42) == "42"

    def test_thousands(self):
        assert format_number(1234) == "1,234"

    def test_millions(self):
        assert format_number(1234567) == "1,234,567"

    def test_zero(self):
        assert format_number(0) == "0"

    def test_negative(self):
        assert format_number(-1500) == "-1,500"


# ═══════════════════════════════════════
# Truncate Path
# ═══════════════════════════════════════

class TestTruncatePath:

    def test_short_path_unchanged(self):
        path = "/Users/test/file.jpg"
        assert truncate_path(path, 40) == path

    def test_long_path_truncated(self):
        path = "/Users/pongtepchithan/Desktop/very/long/nested/deep/folder/file.jpg"
        result = truncate_path(path, 40)
        assert len(result) < len(path)
        assert "..." in result

    def test_custom_max_len(self):
        path = "/a/b/c/d/e/f/g/h/file.jpg"
        result = truncate_path(path, 20)
        assert "..." in result
