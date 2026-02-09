"""
Tests for GeminiEngine retry logic:
  - classify_error maps exceptions to correct GeminiErrorType
  - Retryable vs non-retryable errors
  - _generate_with_retry retries on retryable errors with exponential backoff
  - _generate_with_retry raises immediately on non-retryable errors
  - _parse_json_response handles markdown fences, trailing text, invalid JSON
  - MAX_RETRIES honored
"""
import json
import time
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from core.engines.gemini_engine import (
    GeminiEngine, GeminiError, GeminiErrorType, classify_error,
)
from core.config import MAX_RETRIES


# ═══════════════════════════════════════
# classify_error
# ═══════════════════════════════════════

class TestClassifyError:

    # ── Rate Limit (retryable) ──

    def test_429_rate_limit(self):
        e = classify_error(Exception("429 Resource Exhausted"))
        assert e.error_type == GeminiErrorType.RATE_LIMIT
        assert e.retryable is True

    def test_rate_limit_keyword(self):
        e = classify_error(Exception("Rate limit exceeded"))
        assert e.error_type == GeminiErrorType.RATE_LIMIT
        assert e.retryable is True

    def test_resource_exhausted(self):
        e = classify_error(Exception("RESOURCE_EXHAUSTED"))
        assert e.error_type == GeminiErrorType.RATE_LIMIT

    # ── Quota (NOT retryable) ──

    def test_quota_exceeded(self):
        e = classify_error(Exception("Quota exceeded for project"))
        assert e.error_type == GeminiErrorType.QUOTA
        assert e.retryable is False

    def test_billing_error(self):
        e = classify_error(Exception("Billing account not configured"))
        assert e.error_type == GeminiErrorType.QUOTA
        assert e.retryable is False

    # ── Safety (NOT retryable) ──

    def test_safety_blocked(self):
        e = classify_error(Exception("Response blocked by safety filters"))
        assert e.error_type == GeminiErrorType.SAFETY
        assert e.retryable is False

    def test_harm_content(self):
        e = classify_error(Exception("Content flagged for harm"))
        assert e.error_type == GeminiErrorType.SAFETY

    # ── Timeout (retryable) ──

    def test_timeout(self):
        e = classify_error(Exception("Request timeout after 60s"))
        assert e.error_type == GeminiErrorType.TIMEOUT
        assert e.retryable is True

    def test_deadline_exceeded(self):
        e = classify_error(Exception("Deadline exceeded"))
        assert e.error_type == GeminiErrorType.TIMEOUT
        assert e.retryable is True

    # ── Invalid Key (NOT retryable) ──

    def test_api_key_invalid(self):
        e = classify_error(Exception("API_KEY_INVALID"))
        assert e.error_type == GeminiErrorType.INVALID_KEY
        assert e.retryable is False

    def test_401_unauthorized(self):
        e = classify_error(Exception("401 Unauthorized"))
        assert e.error_type == GeminiErrorType.INVALID_KEY

    # ── Model Not Found (NOT retryable) ──

    def test_model_not_found(self):
        e = classify_error(Exception("Model not found: gemini-99"))
        assert e.error_type == GeminiErrorType.MODEL_NOT_FOUND
        assert e.retryable is False

    def test_404_not_found(self):
        e = classify_error(Exception("404 Not Found"))
        assert e.error_type == GeminiErrorType.MODEL_NOT_FOUND

    # ── Content Too Large (NOT retryable) ──

    def test_payload_too_large(self):
        e = classify_error(Exception("Request payload too large"))
        assert e.error_type == GeminiErrorType.CONTENT_TOO_LARGE
        assert e.retryable is False

    def test_413_entity_too_large(self):
        e = classify_error(Exception("413 Entity Too Large"))
        assert e.error_type == GeminiErrorType.CONTENT_TOO_LARGE

    # ── Unknown (retryable) ──

    def test_unknown_error(self):
        e = classify_error(Exception("Something completely unexpected"))
        assert e.error_type == GeminiErrorType.UNKNOWN
        assert e.retryable is True


# ═══════════════════════════════════════
# GeminiError
# ═══════════════════════════════════════

class TestGeminiError:

    def test_error_attributes(self):
        e = GeminiError("test msg", GeminiErrorType.RATE_LIMIT, retryable=True)
        assert str(e) == "test msg"
        assert e.error_type == GeminiErrorType.RATE_LIMIT
        assert e.retryable is True

    def test_default_not_retryable(self):
        e = GeminiError("msg", GeminiErrorType.SAFETY)
        assert e.retryable is False

    def test_is_exception(self):
        assert issubclass(GeminiError, Exception)

    def test_all_error_types(self):
        expected = {"RATE_LIMIT", "QUOTA", "SAFETY", "TIMEOUT",
                    "INVALID_KEY", "MODEL_NOT_FOUND", "CONTENT_TOO_LARGE", "UNKNOWN"}
        actual = {t.value for t in GeminiErrorType}
        assert actual == expected


# ═══════════════════════════════════════
# _generate_with_retry
# ═══════════════════════════════════════

class TestGenerateWithRetry:

    @pytest.fixture
    def engine(self):
        e = GeminiEngine()
        e._api_key = "test-key"
        return e

    def test_success_on_first_attempt(self, engine):
        """No retries needed when first call succeeds."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.text = '{"title": "Test", "keywords": ["a"]}'
        mock_response.usage_metadata = None
        mock_model.generate_content.return_value = mock_response
        engine._model = mock_model

        result = engine._generate_with_retry(contents=["test"], timeout=30)
        assert result["title"] == "Test"
        assert mock_model.generate_content.call_count == 1

    def test_retries_on_rate_limit(self, engine):
        """Should retry on rate limit (retryable) then succeed."""
        mock_model = MagicMock()
        # First call: rate limit, second call: success
        rate_limit_exc = Exception("429 Resource Exhausted")
        mock_success = MagicMock()
        mock_success.candidates = [MagicMock()]
        mock_success.text = '{"title": "OK"}'
        mock_success.usage_metadata = None
        mock_model.generate_content.side_effect = [rate_limit_exc, mock_success]
        engine._model = mock_model

        with patch("core.engines.gemini_engine.time.sleep"):  # skip actual sleep
            result = engine._generate_with_retry(contents=["test"], timeout=30)
        assert result["title"] == "OK"
        assert mock_model.generate_content.call_count == 2

    def test_retries_on_timeout(self, engine):
        """Should retry on timeout (retryable)."""
        mock_model = MagicMock()
        timeout_exc = Exception("Deadline exceeded")
        mock_success = MagicMock()
        mock_success.candidates = [MagicMock()]
        mock_success.text = '{"title": "Recovered"}'
        mock_success.usage_metadata = None
        mock_model.generate_content.side_effect = [timeout_exc, mock_success]
        engine._model = mock_model

        with patch("core.engines.gemini_engine.time.sleep"):
            result = engine._generate_with_retry(contents=["test"], timeout=30)
        assert result["title"] == "Recovered"

    def test_no_retry_on_safety(self, engine):
        """Should NOT retry on safety block (non-retryable)."""
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("Response blocked by safety filters")
        engine._model = mock_model

        with pytest.raises(GeminiError) as exc_info:
            with patch("core.engines.gemini_engine.time.sleep"):
                engine._generate_with_retry(contents=["test"], timeout=30)
        assert exc_info.value.error_type == GeminiErrorType.SAFETY
        assert mock_model.generate_content.call_count == 1  # no retry

    def test_no_retry_on_invalid_key(self, engine):
        """Should NOT retry on invalid API key."""
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API_KEY_INVALID")
        engine._model = mock_model

        with pytest.raises(GeminiError) as exc_info:
            with patch("core.engines.gemini_engine.time.sleep"):
                engine._generate_with_retry(contents=["test"], timeout=30)
        assert exc_info.value.error_type == GeminiErrorType.INVALID_KEY
        assert mock_model.generate_content.call_count == 1

    def test_no_retry_on_quota(self, engine):
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("Quota exceeded for billing")
        engine._model = mock_model

        with pytest.raises(GeminiError) as exc_info:
            with patch("core.engines.gemini_engine.time.sleep"):
                engine._generate_with_retry(contents=["test"], timeout=30)
        assert exc_info.value.error_type == GeminiErrorType.QUOTA
        assert mock_model.generate_content.call_count == 1

    def test_max_retries_exhausted(self, engine):
        """After MAX_RETRIES attempts, should raise the last error."""
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("429 Rate limit")
        engine._model = mock_model

        with pytest.raises(GeminiError) as exc_info:
            with patch("core.engines.gemini_engine.time.sleep"):
                engine._generate_with_retry(contents=["test"], timeout=30)
        assert exc_info.value.error_type == GeminiErrorType.RATE_LIMIT
        assert mock_model.generate_content.call_count == MAX_RETRIES

    def test_exponential_backoff(self, engine):
        """Verify backoff delays: 2s, 4s, 8s..."""
        mock_model = MagicMock()
        # All attempts fail with retryable error
        mock_model.generate_content.side_effect = Exception("429 Rate limit")
        engine._model = mock_model

        sleep_calls = []
        with patch("core.engines.gemini_engine.time.sleep", side_effect=lambda s: sleep_calls.append(s)):
            with pytest.raises(GeminiError):
                engine._generate_with_retry(contents=["test"], timeout=30)

        # Should have MAX_RETRIES-1 sleep calls (no sleep after last attempt)
        assert len(sleep_calls) == MAX_RETRIES - 1
        # Verify exponential: 2^1=2, 2^2=4
        for i, delay in enumerate(sleep_calls):
            assert delay == 2 ** (i + 1)

    def test_safety_blocked_no_candidates(self, engine):
        """Empty candidates list → safety error."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.candidates = []  # blocked
        mock_model.generate_content.return_value = mock_response
        engine._model = mock_model

        with pytest.raises(GeminiError) as exc_info:
            engine._generate_with_retry(contents=["test"], timeout=30)
        assert exc_info.value.error_type == GeminiErrorType.SAFETY

    def test_already_classified_error_not_wrapped(self, engine):
        """If generate_content raises GeminiError directly, don't re-wrap."""
        mock_model = MagicMock()
        original = GeminiError("Custom safety", GeminiErrorType.SAFETY, retryable=False)
        mock_model.generate_content.side_effect = original
        engine._model = mock_model

        with pytest.raises(GeminiError) as exc_info:
            engine._generate_with_retry(contents=["test"], timeout=30)
        assert exc_info.value is original


# ═══════════════════════════════════════
# _parse_json_response
# ═══════════════════════════════════════

class TestParseJsonResponse:

    @pytest.fixture
    def engine(self):
        return GeminiEngine()

    def test_clean_json(self, engine):
        text = '{"title": "Sunset", "keywords": ["beach"]}'
        result = engine._parse_json_response(text)
        assert result["title"] == "Sunset"

    def test_markdown_json_fence(self, engine):
        text = '```json\n{"title": "Sunset"}\n```'
        result = engine._parse_json_response(text)
        assert result["title"] == "Sunset"

    def test_markdown_plain_fence(self, engine):
        text = '```\n{"title": "Sunset"}\n```'
        result = engine._parse_json_response(text)
        assert result["title"] == "Sunset"

    def test_leading_text(self, engine):
        text = 'Here is the result: {"title": "Sunset"}'
        result = engine._parse_json_response(text)
        assert result["title"] == "Sunset"

    def test_trailing_text(self, engine):
        text = '{"title": "Sunset"} some trailing garbage'
        result = engine._parse_json_response(text)
        assert result["title"] == "Sunset"

    def test_whitespace(self, engine):
        text = '  \n  {"title": "Sunset"}  \n  '
        result = engine._parse_json_response(text)
        assert result["title"] == "Sunset"

    def test_invalid_json_raises(self, engine):
        with pytest.raises(GeminiError) as exc_info:
            engine._parse_json_response("not json at all")
        assert exc_info.value.error_type == GeminiErrorType.UNKNOWN
        assert exc_info.value.retryable is False

    def test_empty_object(self, engine):
        assert engine._parse_json_response("{}") == {}

    def test_nested_json(self, engine):
        text = json.dumps({
            "title": "Test",
            "description": "A test",
            "keywords": ["a", "b"],
            "category": "Nature",
        })
        result = engine._parse_json_response(text)
        assert result["category"] == "Nature"
        assert len(result["keywords"]) == 2

    def test_unicode_in_json(self, engine):
        text = '{"title": "カフェ", "keywords": ["café", "naïve"]}'
        result = engine._parse_json_response(text)
        assert result["title"] == "カフェ"
        assert "café" in result["keywords"]
