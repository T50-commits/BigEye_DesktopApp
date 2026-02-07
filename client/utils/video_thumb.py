"""
BigEye Pro — Video Thumbnail Extractor (FFmpeg)
Extracts the first frame of a video file as a temporary image for preview.
"""
import os
import subprocess
import tempfile
import hashlib

from core.config import APP_DATA_DIR

# Cache directory for video thumbnails
THUMB_CACHE_DIR = os.path.join(APP_DATA_DIR, "thumb_cache")
os.makedirs(THUMB_CACHE_DIR, exist_ok=True)


def _cache_path(video_path: str) -> str:
    """Generate a deterministic cache filename for a video."""
    h = hashlib.md5(video_path.encode()).hexdigest()[:16]
    return os.path.join(THUMB_CACHE_DIR, f"{h}.jpg")


def extract_first_frame(video_path: str) -> str | None:
    """
    Extract the first frame of a video using FFmpeg.
    Returns the path to the extracted JPEG, or None on failure.
    Uses a disk cache so repeated calls are instant.
    """
    if not os.path.isfile(video_path):
        return None

    cached = _cache_path(video_path)
    if os.path.isfile(cached):
        return cached

    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            "-vf", "scale=480:-1",
            cached,
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        if result.returncode == 0 and os.path.isfile(cached):
            return cached
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return None


def cleanup_thumb_cache():
    """Remove all cached video thumbnails."""
    if os.path.isdir(THUMB_CACHE_DIR):
        for f in os.listdir(THUMB_CACHE_DIR):
            try:
                os.remove(os.path.join(THUMB_CACHE_DIR, f))
            except OSError:
                pass
