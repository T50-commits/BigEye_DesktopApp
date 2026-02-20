"""
BigEye Pro — Gemini AI Engine (Task B-06)
Handles all interactions with Google Gemini API for metadata generation.
Features: context caching, error classification, retry logic, photo/video processing.
"""
import json
import time
import logging
import os
import threading
from datetime import timedelta
from enum import Enum
from typing import Optional

import google.generativeai as genai
from google.generativeai import caching as genai_caching

from core.config import MAX_RETRIES, TIMEOUT_PHOTO, TIMEOUT_VIDEO

logger = logging.getLogger("bigeye")


# ═══════════════════════════════════════
# Error Classification
# ═══════════════════════════════════════

class GeminiErrorType(Enum):
    """Classified error types from Gemini API."""
    RATE_LIMIT = "RATE_LIMIT"
    QUOTA = "QUOTA"
    SAFETY = "SAFETY"
    TIMEOUT = "TIMEOUT"
    INVALID_KEY = "INVALID_KEY"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    CONTENT_TOO_LARGE = "CONTENT_TOO_LARGE"
    UNKNOWN = "UNKNOWN"


class GeminiError(Exception):
    """Classified Gemini API error."""
    def __init__(self, message: str, error_type: GeminiErrorType, retryable: bool = False):
        super().__init__(message)
        self.error_type = error_type
        self.retryable = retryable


def classify_error(exc: Exception) -> GeminiError:
    """Classify a raw Gemini API exception into a GeminiError."""
    msg = str(exc).lower()

    if "rate" in msg and "limit" in msg or "429" in msg or "resource_exhausted" in msg:
        return GeminiError(str(exc), GeminiErrorType.RATE_LIMIT, retryable=True)
    elif "quota" in msg or "billing" in msg:
        return GeminiError(str(exc), GeminiErrorType.QUOTA, retryable=False)
    elif "safety" in msg or "blocked" in msg or "harm" in msg:
        return GeminiError(str(exc), GeminiErrorType.SAFETY, retryable=False)
    elif "timeout" in msg or "deadline" in msg or "timed out" in msg or "read operation" in msg:
        return GeminiError(str(exc), GeminiErrorType.TIMEOUT, retryable=True)
    elif "ssl" in msg or "wrong_version_number" in msg or "certificate" in msg:
        return GeminiError(str(exc), GeminiErrorType.TIMEOUT, retryable=True)
    elif "httperror" in msg or "http error" in msg:
        return GeminiError(str(exc), GeminiErrorType.UNKNOWN, retryable=True)
    elif "api_key" in msg or "invalid" in msg and "key" in msg or "401" in msg:
        return GeminiError(str(exc), GeminiErrorType.INVALID_KEY, retryable=False)
    elif "not found" in msg and "model" in msg or "404" in msg:
        return GeminiError(str(exc), GeminiErrorType.MODEL_NOT_FOUND, retryable=False)
    elif ("too large" in msg or "payload" in msg or "413" in msg) and "403" not in msg and "permission" not in msg:
        return GeminiError(str(exc), GeminiErrorType.CONTENT_TOO_LARGE, retryable=False)
    else:
        return GeminiError(str(exc), GeminiErrorType.UNKNOWN, retryable=True)


# ═══════════════════════════════════════
# Gemini Engine
# ═══════════════════════════════════════

class GeminiEngine:
    """Client-side Gemini AI engine for generating stock metadata."""

    def __init__(self):
        self._api_key = ""
        self._model_name = "gemini-2.5-pro"
        self._model = None
        self._cache = None
        self._cache_name = ""
        self._system_prompt = ""                 # Stored for inline system_instruction
        self._model_lock = threading.Lock()           # Protect lazy model creation
        self._api_sem = threading.Semaphore(6)          # Allow parallel generates
        self._upload_lock = threading.Lock()            # Serialize video uploads (SSL corruption fix)
        self._prefetch_lock = threading.Lock()          # Protect prefetched dict
        self._prefetched = {}                           # {filepath: video_file} pre-uploaded videos

    # ── Configuration ──

    def set_api_key(self, key: str):
        """Set the Gemini API key and configure the client."""
        self._api_key = key
        genai.configure(api_key=key, transport="rest")
        self._model = None  # Reset model when key changes

    def set_model(self, model_name: str):
        """Set the model name (e.g. gemini-2.5-pro)."""
        self._model_name = model_name
        self._model = None  # Reset model when name changes

    def set_system_prompt(self, system_prompt: str):
        """Set system prompt for inline system_instruction (fallback when cache unavailable)."""
        if system_prompt != self._system_prompt:
            self._system_prompt = system_prompt
            self._model = None  # Rebuild model with new system_instruction

    def _get_model(self) -> genai.GenerativeModel:
        """Get or create the GenerativeModel instance (thread-safe)."""
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    gen_config = genai.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.3,
                    )
                    if self._cache:
                        # SDK 0.8+ requires from_cached_content() instead of cached_content kwarg
                        try:
                            self._model = genai.GenerativeModel.from_cached_content(
                                cached_content=self._cache,
                                generation_config=gen_config,
                            )
                        except Exception as e:
                            logger.warning(f"from_cached_content failed: {e} — falling back to system_instruction")
                            self._cache = None
                            self._cache_name = ""
                            self._model = genai.GenerativeModel(
                                model_name=self._model_name,
                                generation_config=gen_config,
                                system_instruction=self._system_prompt or None,
                            )
                    else:
                        self._model = genai.GenerativeModel(
                            model_name=self._model_name,
                            generation_config=gen_config,
                            system_instruction=self._system_prompt or None,
                        )
        return self._model

    # ── Context Caching ──

    def create_cache(self, system_prompt: str, display_name: str = "bigeye-prompt",
                     ttl_minutes: int = 60) -> str:
        """
        Create a context cache with the system prompt.
        Returns the cache name/ID.
        """
        try:
            self._cache = genai_caching.CachedContent.create(
                model=self._model_name,
                display_name=display_name,
                system_instruction=system_prompt,
                ttl=timedelta(minutes=ttl_minutes),
            )
            self._cache_name = self._cache.name
            self._model = None  # Reset to pick up cached content
            logger.info(f"Context cache created: {self._cache_name}")
            return self._cache_name
        except Exception as e:
            logger.warning(f"Failed to create context cache: {e}")
            # Fallback: use system instruction without caching
            self._cache = None
            self._cache_name = ""
            return ""

    def delete_cache(self):
        """Delete the current context cache."""
        if self._cache:
            try:
                self._cache.delete()
                logger.info(f"Cache deleted: {self._cache_name}")
            except Exception as e:
                logger.debug(f"Cache delete failed: {e}")
            finally:
                self._cache = None
                self._cache_name = ""
                self._model = None

    def cleanup_orphaned_caches(self):
        """Delete stale context caches from previous sessions."""
        if not self._api_key:
            return
        try:
            for cache in genai_caching.CachedContent.list():
                if hasattr(cache, 'display_name') and cache.display_name and \
                   cache.display_name.startswith("bigeye"):
                    try:
                        cache.delete()
                        logger.debug(f"Cleaned orphaned cache: {cache.name}")
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Cache cleanup skipped: {e}")

    # ── Processing ──

    def process_photo(self, filepath: str, prompt: str,
                      system_prompt: str = "") -> dict:
        """
        Process a photo file with Gemini API.
        Returns parsed JSON dict with title, description, keywords, category.
        Raises GeminiError on classified failure.
        """
        image_data = self._load_image(filepath)
        return self._generate_with_retry(
            contents=[image_data, prompt],
            system_prompt=system_prompt,
            timeout=TIMEOUT_PHOTO,
        )

    def prefetch_video(self, filepath: str):
        """Pre-upload video. จำกัดไม่เกิน 2 ไฟล์ค้างใน prefetched."""
        with self._prefetch_lock:
            if len(self._prefetched) >= 2:
                logger.debug("Prefetch skipped: already 2 files queued")
                return
        try:
            video_file = self._upload_video(filepath)
            with self._prefetch_lock:
                self._prefetched[filepath] = video_file
            logger.info(f"Prefetched video: {os.path.basename(filepath)}")
        except Exception as e:
            logger.warning(f"Prefetch failed for {os.path.basename(filepath)}: {e}")
            # Don't store — process_video will upload normally

    def process_video(self, filepath: str, prompt: str,
                      system_prompt: str = "") -> dict:
        """
        Process a video file with Gemini API.
        Uses prefetched upload if available, otherwise uploads now.
        Video generate is serialized to prevent SSL corruption,
        but upload runs in parallel with generate (pipeline).
        """
        # Use prefetched upload if available
        with self._prefetch_lock:
            video_file = self._prefetched.pop(filepath, None)
        if video_file:
            logger.info(f"Using prefetched upload: {video_file.name}")
        else:
            video_file = self._upload_video(filepath)
        try:
            return self._generate_with_retry(
                contents=[video_file, prompt],
                system_prompt=system_prompt,
                timeout=TIMEOUT_VIDEO,
            )
        finally:
            try:
                genai.delete_file(video_file.name)
            except Exception:
                pass  # ข้ามไป Gemini ลบเองใน 48 ชม.

    def cleanup_prefetched(self):
        """Delete any prefetched videos that were never used."""
        for fp, vf in self._prefetched.items():
            try:
                genai.delete_file(vf.name)
                logger.debug(f"Cleaned prefetched: {vf.name}")
            except Exception:
                pass
        self._prefetched.clear()

    # ── Internal helpers ──

    def _load_image(self, filepath: str) -> dict:
        """Load image file as inline data for Gemini."""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filepath)
        if not mime_type:
            mime_type = "image/jpeg"

        with open(filepath, "rb") as f:
            data = f.read()

        return {
            "mime_type": mime_type,
            "data": data,
        }

    def _reset_client(self):
        """Reset genai client (REST transport — rarely needed)."""
        if self._api_key:
            genai.configure(api_key=self._api_key, transport="rest")
            logger.info("Gemini client reset")

    def cleanup_all_remote_files(self):
        """ลบไฟล์ที่ค้างใน Gemini File API (เรียกครั้งเดียวตอนเริ่ม job)
        ข้าม 403 ทันที ไม่ retry — หยุดหลังลบได้ 10 ตัว"""
        if not self._api_key:
            return
        count = 0
        try:
            for f in genai.list_files():
                try:
                    genai.delete_file(f.name)
                    count += 1
                except Exception:
                    pass  # ข้ามทันที ไม่ retry
                if count >= 10:
                    break  # ลบพอแล้ว ไม่ต้องลบทั้งหมด
            if count:
                logger.info(f"Cleaned {count} old files")
        except Exception:
            pass

    def _upload_video(self, filepath: str):
        """Upload video to Gemini File API. Serialized with timeout to prevent SSL corruption."""
        logger.info(f"Uploading video: {os.path.basename(filepath)}")
        max_upload_retries = 5
        for attempt in range(1, max_upload_retries + 1):
            try:
                # timeout=180s ป้องกัน deadlock ถ้า upload ค้าง
                acquired = self._upload_lock.acquire(timeout=180)
                if not acquired:
                    raise GeminiError(
                        "Video upload timeout — อัพโหลดวิดีโอนานเกินไป กรุณาลองใหม่",
                        GeminiErrorType.TIMEOUT, retryable=True,
                    )
                try:
                    video_file = genai.upload_file(filepath)
                finally:
                    self._upload_lock.release()
                break
            except GeminiError:
                raise  # ไม่ retry timeout จาก lock
            except Exception as e:
                msg = str(e).lower()
                is_retryable = (
                    "ssl" in msg or "wrong_version_number" in msg or
                    "timeout" in msg or "timed out" in msg or "read operation" in msg or
                    "connection" in msg or "network" in msg or
                    "httperror" in msg or "http error" in msg
                )
                if is_retryable and attempt < max_upload_retries:
                    logger.warning(f"Video upload error (attempt {attempt}/{max_upload_retries}): {e}")
                    if "ssl" in msg or "wrong_version_number" in msg:
                        self._reset_client()
                    backoff = min(3 ** attempt, 30)
                    time.sleep(backoff)
                    continue
                raise

        # Wait for video to be processed (ACTIVE state)
        max_wait = 120
        elapsed = 0
        while video_file.state.name == "PROCESSING" and elapsed < max_wait:
            time.sleep(2)
            elapsed += 2
            video_file = genai.get_file(video_file.name)

        if video_file.state.name == "FAILED":
            # ลบไฟล์ที่ FAILED แล้ว retry upload อีกครั้ง
            try:
                genai.delete_file(video_file.name)
            except Exception:
                pass
            logger.warning(f"Video FAILED on Gemini side, retrying upload...")
            time.sleep(3)
            acquired = self._upload_lock.acquire(timeout=180)
            if not acquired:
                raise GeminiError(
                    "Video upload timeout — อัพโหลดวิดีโอนานเกินไป กรุณาลองใหม่",
                    GeminiErrorType.TIMEOUT, retryable=True,
                )
            try:
                video_file = genai.upload_file(filepath)
            finally:
                self._upload_lock.release()
            elapsed = 0
            while video_file.state.name == "PROCESSING" and elapsed < max_wait:
                time.sleep(2)
                elapsed += 2
                video_file = genai.get_file(video_file.name)
            if video_file.state.name != "ACTIVE":
                raise GeminiError(
                    f"Gemini ไม่สามารถประมวลผลวิดีโอนี้ได้ กรุณาลองใหม่",
                    GeminiErrorType.UNKNOWN, retryable=False,
                )

        if video_file.state.name != "ACTIVE":
            raise GeminiError(
                f"วิดีโอไม่พร้อมหลังรอ {max_wait} วินาที กรุณาลองใหม่",
                GeminiErrorType.TIMEOUT, retryable=True,
            )

        logger.info(f"Video ready: {video_file.name}")
        return video_file

    def _generate_with_retry(self, contents: list, system_prompt: str = "",
                             timeout: int = 60) -> dict:
        """
        Call Gemini generate_content with retry logic.
        Retries up to MAX_RETRIES for retryable errors with exponential backoff.
        Returns parsed JSON response dict.
        """
        # Store system_prompt so _get_model can embed it as system_instruction
        if system_prompt and system_prompt != self._system_prompt:
            self._system_prompt = system_prompt
            self._model = None  # Force model rebuild with new system_instruction

        model = self._get_model()
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                with self._api_sem:
                    response = model.generate_content(
                        contents,
                        request_options={"timeout": timeout},
                    )

                # Check for blocked response
                if not response.candidates:
                    raise GeminiError(
                        "Response blocked by safety filters",
                        GeminiErrorType.SAFETY, retryable=False,
                    )

                # Parse JSON from response
                text = response.text.strip()
                result = self._parse_json_response(text)

                # Add token usage info
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    result["_token_input"] = getattr(
                        response.usage_metadata, 'prompt_token_count', 0
                    )
                    result["_token_output"] = getattr(
                        response.usage_metadata, 'candidates_token_count', 0
                    )

                return result

            except GeminiError:
                raise  # Already classified, don't wrap again
            except Exception as e:
                last_error = classify_error(e)
                logger.warning(
                    f"Gemini attempt {attempt}/{MAX_RETRIES}: "
                    f"[{last_error.error_type.value}] {last_error}"
                )

                if not last_error.retryable or attempt >= MAX_RETRIES:
                    raise last_error

                # Reset client on SSL/connection errors
                raw_msg = str(e).lower()
                if "ssl" in raw_msg or "wrong_version_number" in raw_msg or "connection" in raw_msg:
                    self._reset_client()
                    model = self._get_model()

                # Exponential backoff: 2s, 4s, 8s...
                backoff = 2 ** attempt
                logger.info(f"Retrying in {backoff}s...")
                time.sleep(backoff)

        raise last_error  # Should not reach here, but safety net

    def _parse_json_response(self, text: str) -> dict:
        """
        Parse JSON from Gemini response text.
        Handles markdown code fences and trailing garbage.
        """
        # Strip markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove only first line (```json) and last line (```)
            if len(lines) >= 2:
                if lines[-1].strip() == "```":
                    lines = lines[1:-1]
                else:
                    lines = lines[1:]
            text = "\n".join(lines)

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass

            # Show more context in error message
            preview = text[:300] if len(text) > 300 else text
            raise GeminiError(
                f"Cannot parse JSON from response. Preview: {preview}",
                GeminiErrorType.UNKNOWN, retryable=False,
            )
