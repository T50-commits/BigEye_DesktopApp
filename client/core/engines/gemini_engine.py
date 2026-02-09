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

    # HttpError 200 — Google API client lib bug (response parsing failure on success)
    if "httperror" in msg and "200" in msg:
        return GeminiError(str(exc), GeminiErrorType.UNKNOWN, retryable=True)
    elif "rate" in msg and "limit" in msg or "429" in msg or "resource_exhausted" in msg:
        return GeminiError(str(exc), GeminiErrorType.RATE_LIMIT, retryable=True)
    elif "quota" in msg or "billing" in msg:
        return GeminiError(str(exc), GeminiErrorType.QUOTA, retryable=False)
    elif "safety" in msg or "blocked" in msg or "harm" in msg:
        return GeminiError(str(exc), GeminiErrorType.SAFETY, retryable=False)
    elif "timeout" in msg or "deadline" in msg or "timed out" in msg:
        return GeminiError(str(exc), GeminiErrorType.TIMEOUT, retryable=True)
    elif "ssl" in msg or "wrong_version_number" in msg or "certificate" in msg:
        return GeminiError(str(exc), GeminiErrorType.TIMEOUT, retryable=True)
    elif "api_key" in msg or "invalid" in msg and "key" in msg or "401" in msg:
        return GeminiError(str(exc), GeminiErrorType.INVALID_KEY, retryable=False)
    elif "not found" in msg and "model" in msg or "404" in msg:
        return GeminiError(str(exc), GeminiErrorType.MODEL_NOT_FOUND, retryable=False)
    elif "too large" in msg or "payload" in msg or "413" in msg:
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
        self._model_lock = threading.Lock()      # Protect lazy model creation
        self._api_sem = threading.Semaphore(3)   # Allow up to 3 concurrent API calls

    # ── Configuration ──

    def set_api_key(self, key: str):
        """Set the Gemini API key and configure the client."""
        self._api_key = key
        genai.configure(api_key=key)
        self._model = None  # Reset model when key changes

    def set_model(self, model_name: str):
        """Set the model name (e.g. gemini-2.5-pro)."""
        self._model_name = model_name
        self._model = None  # Reset model when name changes

    def _get_model(self) -> genai.GenerativeModel:
        """Get or create the GenerativeModel instance (thread-safe)."""
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    kwargs = {
                        "model_name": self._model_name,
                        "generation_config": genai.GenerationConfig(
                            response_mime_type="application/json",
                            temperature=0.3,
                        ),
                    }
                    if self._cache:
                        kwargs["cached_content"] = self._cache
                    self._model = genai.GenerativeModel(**kwargs)
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
                ttl=f"{ttl_minutes * 60}s",
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

    def process_video(self, filepath: str, prompt: str,
                      system_prompt: str = "") -> dict:
        """
        Process a video file with Gemini API.
        Uploads video, waits for processing, then generates.
        Returns parsed JSON dict.
        Raises GeminiError on classified failure.
        """
        video_file = self._upload_video(filepath)
        try:
            return self._generate_with_retry(
                contents=[video_file, prompt],
                system_prompt=system_prompt,
                timeout=TIMEOUT_VIDEO,
            )
        finally:
            # Clean up uploaded file
            try:
                genai.delete_file(video_file.name)
            except Exception:
                pass

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

    def _upload_video(self, filepath: str):
        """Upload video to Gemini File API and wait for processing."""
        logger.info(f"Uploading video: {os.path.basename(filepath)}")
        max_upload_retries = 3
        for attempt in range(1, max_upload_retries + 1):
            try:
                with self._api_sem:
                    video_file = genai.upload_file(filepath)
                break
            except Exception as e:
                msg = str(e).lower()
                if ("ssl" in msg or "wrong_version_number" in msg) and attempt < max_upload_retries:
                    logger.warning(f"Video upload SSL error (attempt {attempt}): {e}")
                    time.sleep(2 ** attempt)
                    continue
                raise

        # Wait for video to be processed (ACTIVE state)
        max_wait = 180  # seconds
        elapsed = 0
        while video_file.state.name == "PROCESSING" and elapsed < max_wait:
            time.sleep(3)
            elapsed += 3
            try:
                video_file = genai.get_file(video_file.name)
            except Exception as poll_err:
                # Transient errors during polling (incl. HttpError 200) — retry
                logger.warning(f"get_file poll error (elapsed {elapsed}s): {poll_err}")
                if elapsed >= max_wait:
                    raise
                time.sleep(2)
                continue

        if video_file.state.name == "FAILED":
            raise GeminiError(
                f"Video processing failed: {video_file.name}",
                GeminiErrorType.UNKNOWN, retryable=False,
            )

        if video_file.state.name != "ACTIVE":
            raise GeminiError(
                f"Video not ready after {max_wait}s: state={video_file.state.name}",
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
        model = self._get_model()
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Build request kwargs
                kwargs = {"contents": contents}
                if system_prompt and not self._cache:
                    # If no cache, pass system prompt inline
                    kwargs["generation_config"] = genai.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.3,
                    )

                with self._api_sem:
                    response = model.generate_content(
                        contents,
                        request_options={"timeout": (30, timeout)},
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

            raise GeminiError(
                f"Cannot parse JSON from response: {text[:200]}",
                GeminiErrorType.UNKNOWN, retryable=False,
            )
