"""
BigEye Pro — Video Transcoder (Task B-08)
Creates 480p proxy videos using FFmpeg for Gemini upload.
Features: proxy creation, duration detection, cleanup, FFmpeg availability check.
"""
import os
import json
import logging
import subprocess
import tempfile

from core.config import APP_DATA_DIR

logger = logging.getLogger("bigeye")

PROXY_DIR = os.path.join(APP_DATA_DIR, "proxy_cache")
os.makedirs(PROXY_DIR, exist_ok=True)


class Transcoder:
    """FFmpeg-based video transcoder for creating proxy clips."""

    @staticmethod
    def is_ffmpeg_available() -> bool:
        """Check if FFmpeg is installed and accessible."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, OSError):
            return False

    @staticmethod
    def get_duration(filepath: str) -> float:
        """Get video duration in seconds using ffprobe. Returns 0.0 on failure."""
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                filepath,
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                info = json.loads(result.stdout)
                return float(info.get("format", {}).get("duration", 0))
        except Exception:
            pass
        return 0.0

    @staticmethod
    def get_proxy_path(input_path: str) -> str:
        """Generate a deterministic proxy path in the cache directory."""
        import hashlib
        name_hash = hashlib.md5(input_path.encode()).hexdigest()[:12]
        base = os.path.splitext(os.path.basename(input_path))[0]
        return os.path.join(PROXY_DIR, f"{base}_{name_hash}_480p.mp4")

    @staticmethod
    def create_proxy(input_path: str, output_path: str = "",
                     height: int = 360, max_duration: int = 30) -> str:
        """
        Create a heavily compressed proxy video for Gemini upload.
        Resolution: 360p (or lower), Framerate: 8fps, Max Duration: 30s.
        Returns output path on success, empty string on failure.
        """
        if not output_path:
            output_path = Transcoder.get_proxy_path(input_path)

        # Skip if proxy already exists and is newer than source
        if os.path.isfile(output_path):
            if os.path.getmtime(output_path) >= os.path.getmtime(input_path):
                logger.debug(f"Proxy cache hit: {output_path}")
                return output_path

        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
            ]

            # Duration limit (Aggressive cap at 30s for AI to just see the context)
            if max_duration > 0:
                cmd.extend(["-t", str(max_duration)])

            cmd.extend([
                "-vf", f"scale=-2:{height}",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "36",       # High compression
                "-r", "8",          # Very low framerate (sufficient for AI)
                "-an",              # No audio
                output_path,
            ])

            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=120, # Reduced timeout for faster fail
            )

            if result.returncode == 0 and os.path.isfile(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                logger.info(f"Proxy created: {os.path.basename(output_path)} ({size_mb:.1f} MB)")
                return output_path
            else:
                stderr = result.stderr.decode(errors="replace")[-200:] if result.stderr else ""
                logger.warning(f"Proxy creation failed: {stderr}")
                return ""

        except subprocess.TimeoutExpired:
            logger.warning(f"Proxy creation timed out: {input_path}")
            return ""
        except (FileNotFoundError, OSError) as e:
            logger.warning(f"FFmpeg not found or OS error: {e}")
            return ""

    @staticmethod
    def cleanup_proxy(proxy_path: str):
        """Delete a proxy file."""
        try:
            if proxy_path and os.path.isfile(proxy_path):
                os.remove(proxy_path)
        except OSError:
            pass

    @staticmethod
    def cleanup_all_proxies():
        """Delete all proxy files in the cache directory."""
        try:
            for f in os.listdir(PROXY_DIR):
                fp = os.path.join(PROXY_DIR, f)
                if os.path.isfile(fp):
                    os.remove(fp)
            logger.info("Proxy cache cleared")
        except OSError as e:
            logger.debug(f"Proxy cleanup error: {e}")
