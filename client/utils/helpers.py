"""
BigEye Pro — Helper Utilities
"""
import os
import platform
import hashlib
import uuid

from core.config import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS


def get_hardware_id() -> str:
    """Generate a unique hardware ID for device binding."""
    info = f"{platform.node()}-{platform.machine()}-{uuid.getnode()}"
    return hashlib.sha256(info.encode()).hexdigest()[:32]


def is_image(filepath: str) -> bool:
    """Check if file is a supported image."""
    ext = os.path.splitext(filepath)[1].lower()
    return ext in IMAGE_EXTENSIONS


def is_video(filepath: str) -> bool:
    """Check if file is a supported video."""
    ext = os.path.splitext(filepath)[1].lower()
    return ext in VIDEO_EXTENSIONS


def is_supported_file(filepath: str) -> bool:
    """Check if file is a supported media file."""
    return is_image(filepath) or is_video(filepath)


def scan_folder(folder_path: str) -> list:
    """Scan folder for supported media files. Returns list of absolute paths."""
    if not folder_path or not os.path.isdir(folder_path):
        return []
    files = []
    for fname in sorted(os.listdir(folder_path)):
        fpath = os.path.join(folder_path, fname)
        if os.path.isfile(fpath) and is_supported_file(fpath):
            files.append(fpath)
    return files


def count_files(file_list: list) -> tuple:
    """Count images and videos in file list. Returns (image_count, video_count)."""
    images = sum(1 for f in file_list if is_image(f))
    videos = sum(1 for f in file_list if is_video(f))
    return images, videos


def format_number(n: int) -> str:
    """Format number with comma separator."""
    return f"{n:,}"


def truncate_path(path: str, max_len: int = 40) -> str:
    """Truncate a file path for display."""
    if len(path) <= max_len:
        return path
    parts = path.split(os.sep)
    if len(parts) <= 3:
        return path
    return os.sep.join(parts[:2]) + os.sep + "..." + os.sep + os.sep.join(parts[-2:])
