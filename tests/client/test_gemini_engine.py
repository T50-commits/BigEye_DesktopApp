"""
Tests for client/core/engines/gemini_engine.py
Covers: classify_error, GeminiError, GeminiErrorType, _parse_json_response,
        _load_image, engine configuration, double-check locking.
"""
import json
import pytest
from unittest.mock import patch, MagicMock, mock_open

from core.engines.gemini_engine import (
    GeminiEngine,
    GeminiError,
    GeminiErrorType,
    classify_error,
)


# ═══════════════════════════════════════
# GeminiError / GeminiErrorType
# ═══════════════════════════════════════

class TestGeminiError:

    def test_error_has_type_and_retryable(self):
        e = GeminiError("rate limited", GeminiErrorType.RATE_LIMIT, retryable=True)
        assert e.error_type == GeminiErrorType.RATE_LIMIT
        assert e.retryable is True
        assert str(e) == "rate limited"

    def test_error_default_not_retryable(self):
        e = GeminiError("bad key", GeminiErrorType.INVALID_KEY)
        assert e.retryable is False

    def test_all_error_types_exist(self):
        expected = {
            "RATE_LIMIT", "QUOTA", "SAFETY", "TIMEOUT",
            "INVALID_KEY", "MODEL_NOT_FOUND", "CONTENT_TOO_LARGE", "UNKNOWN",
        }
        actual = {t.value for t in GeminiErrorType}
        assert actual == expected


# ═══════════════════════════════════════
# classify_error
# ═══════════════════════════════════════

class TestClassifyError:

    def test_rate_limit_429(self):
        e = classify_error(Exception("429 Resource Exhausted"))
        assert e.error_type == GeminiErrorType.RATE_LIMIT
        assert e.retryable is True

    def test_rate_limit_keyword(self):
        e = classify_error(Exception("Rate limit exceeded"))
        assert e.error_type == GeminiErrorType.RATE_LIMIT

    def test_resource_exhausted(self):
        e = classify_error(Exception("RESOURCE_EXHAUSTED: quota"))
        assert e.error_type == GeminiErrorType.RATE_LIMIT

    def test_quota(self):
        e = classify_error(Exception("Quota exceeded for billing"))
        assert e.error_type == GeminiErrorType.QUOTA
        assert e.retryable is False

    def test_billing(self):
        e = classify_error(Exception("Billing account not configured"))
        assert e.error_type == GeminiErrorType.QUOTA

    def test_safety_blocked(self):
        e = classify_error(Exception("Response blocked by safety filters"))
        assert e.error_type == GeminiErrorType.SAFETY
        assert e.retryable is False

    def test_safety_harm(self):
        e = classify_error(Exception("Content flagged for harm"))
        assert e.error_type == GeminiErrorType.SAFETY

    def test_timeout(self):
        e = classify_error(Exception("Request timeout after 60s"))
        assert e.error_type == GeminiErrorType.TIMEOUT
        assert e.retryable is True

    def test_deadline(self):
        e = classify_error(Exception("Deadline exceeded"))
        assert e.error_type == GeminiErrorType.TIMEOUT

    def test_invalid_api_key(self):
        e = classify_error(Exception("API_KEY_INVALID"))
        assert e.error_type == GeminiErrorType.INVALID_KEY
        assert e.retryable is False

    def test_invalid_key_401(self):
        e = classify_error(Exception("401 Unauthorized"))
        assert e.error_type == GeminiErrorType.INVALID_KEY

    def test_model_not_found(self):
        e = classify_error(Exception("Model not found: gemini-99"))
        assert e.error_type == GeminiErrorType.MODEL_NOT_FOUND
        assert e.retryable is False

    def test_404(self):
        e = classify_error(Exception("404 Not Found"))
        assert e.error_type == GeminiErrorType.MODEL_NOT_FOUND

    def test_content_too_large(self):
        e = classify_error(Exception("Request payload too large"))
        assert e.error_type == GeminiErrorType.CONTENT_TOO_LARGE
        assert e.retryable is False

    def test_413(self):
        e = classify_error(Exception("413 Entity Too Large"))
        assert e.error_type == GeminiErrorType.CONTENT_TOO_LARGE

    def test_unknown_error(self):
        e = classify_error(Exception("Something completely unexpected"))
        assert e.error_type == GeminiErrorType.UNKNOWN
        assert e.retryable is True


# ═══════════════════════════════════════
# _parse_json_response
# ═══════════════════════════════════════

class TestParseJsonResponse:

    @pytest.fixture
    def engine(self):
        return GeminiEngine()

    def test_parse_clean_json(self, engine):
        text = '{"title": "Sunset", "keywords": ["beach", "ocean"]}'
        result = engine._parse_json_response(text)
        assert result["title"] == "Sunset"
        assert result["keywords"] == ["beach", "ocean"]

    def test_parse_with_markdown_fences(self, engine):
        text = '```json\n{"title": "Sunset"}\n```'
        result = engine._parse_json_response(text)
        assert result["title"] == "Sunset"

    def test_parse_with_markdown_fences_no_lang(self, engine):
        text = '```\n{"title": "Sunset"}\n```'
        result = engine._parse_json_response(text)
        assert result["title"] == "Sunset"

    def test_parse_with_leading_text(self, engine):
        text = 'Here is the result: {"title": "Sunset", "keywords": []}'
        result = engine._parse_json_response(text)
        assert result["title"] == "Sunset"

    def test_parse_with_trailing_text(self, engine):
        text = '{"title": "Sunset"} some trailing garbage'
        result = engine._parse_json_response(text)
        assert result["title"] == "Sunset"

    def test_parse_with_whitespace(self, engine):
        text = '  \n  {"title": "Sunset"}  \n  '
        result = engine._parse_json_response(text)
        assert result["title"] == "Sunset"

    def test_parse_invalid_json_raises(self, engine):
        with pytest.raises(GeminiError) as exc_info:
            engine._parse_json_response("not json at all")
        assert exc_info.value.error_type == GeminiErrorType.UNKNOWN

    def test_parse_nested_json(self, engine):
        text = json.dumps({
            "title": "Test",
            "description": "A test",
            "keywords": ["a", "b"],
            "category": "Nature",
        })
        result = engine._parse_json_response(text)
        assert result["category"] == "Nature"

    def test_parse_empty_object(self, engine):
        result = engine._parse_json_response("{}")
        assert result == {}


# ═══════════════════════════════════════
# Engine Configuration
# ═══════════════════════════════════════

class TestEngineConfiguration:

    def test_initial_state(self):
        engine = GeminiEngine()
        assert engine._api_key == ""
        assert engine._model_name == "gemini-2.5-pro"
        assert engine._model is None
        assert engine._cache is None

    def test_set_api_key_resets_model(self):
        engine = GeminiEngine()
        engine._model = MagicMock()  # simulate existing model
        with patch("core.engines.gemini_engine.genai"):
            engine.set_api_key("test-key")
        assert engine._api_key == "test-key"
        assert engine._model is None  # reset

    def test_set_model_resets_model(self):
        engine = GeminiEngine()
        engine._model = MagicMock()
        engine.set_model("gemini-2.0-flash")
        assert engine._model_name == "gemini-2.0-flash"
        assert engine._model is None  # reset

    def test_delete_cache_when_no_cache(self):
        engine = GeminiEngine()
        engine.delete_cache()  # Should not raise

    def test_delete_cache_clears_state(self):
        engine = GeminiEngine()
        engine._cache = MagicMock()
        engine._cache_name = "test-cache"
        engine._model = MagicMock()
        engine.delete_cache()
        assert engine._cache is None
        assert engine._cache_name == ""
        assert engine._model is None

    def test_delete_cache_handles_exception(self):
        engine = GeminiEngine()
        engine._cache = MagicMock()
        engine._cache.delete.side_effect = Exception("API error")
        engine._cache_name = "test-cache"
        engine.delete_cache()  # Should not raise
        assert engine._cache is None

    def test_load_image(self, tmp_path):
        engine = GeminiEngine()
        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
        result = engine._load_image(str(img_path))
        assert "mime_type" in result
        assert "data" in result
        assert result["mime_type"] == "image/jpeg"
        assert len(result["data"]) > 0

    def test_load_image_unknown_mime(self, tmp_path):
        engine = GeminiEngine()
        img_path = tmp_path / "test.qqqzzz"
        img_path.write_bytes(b"\x00" * 100)
        result = engine._load_image(str(img_path))
        assert result["mime_type"] == "image/jpeg"  # fallback


# ═══════════════════════════════════════
# _get_model (double-check locking)
# ═══════════════════════════════════════

class TestGetModel:

    def test_creates_model_lazily(self):
        engine = GeminiEngine()
        engine._api_key = "test-key"
        with patch("core.engines.gemini_engine.genai") as mock_genai:
            mock_model = MagicMock()
            mock_genai.GenerativeModel.return_value = mock_model
            mock_genai.GenerationConfig.return_value = MagicMock()
            result = engine._get_model()
            assert result == mock_model
            mock_genai.GenerativeModel.assert_called_once()

    def test_reuses_existing_model(self):
        engine = GeminiEngine()
        mock_model = MagicMock()
        engine._model = mock_model
        with patch("core.engines.gemini_engine.genai") as mock_genai:
            result = engine._get_model()
            assert result == mock_model
            mock_genai.GenerativeModel.assert_not_called()

    def test_includes_cache_when_set(self):
        engine = GeminiEngine()
        engine._api_key = "test-key"
        mock_cache = MagicMock()
        engine._cache = mock_cache
        with patch("core.engines.gemini_engine.genai") as mock_genai:
            mock_genai.GenerativeModel.return_value = MagicMock()
            mock_genai.GenerationConfig.return_value = MagicMock()
            engine._get_model()
            call_kwargs = mock_genai.GenerativeModel.call_args
            assert call_kwargs.kwargs.get("cached_content") == mock_cache
