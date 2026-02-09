"""
Tests for client/core/logic/keyword_processor.py
Covers: _clean, _dedup_case_insensitive, _stem_dedup, _filter_blacklist,
        process_istock, process_hybrid, process_single pipelines.
"""
import pytest
from unittest.mock import patch

from core.logic.keyword_processor import KeywordProcessor, GENERIC_BLACKLIST, IRREGULAR_MAP


@pytest.fixture
def processor():
    return KeywordProcessor()


@pytest.fixture
def processor_with_blacklist():
    p = KeywordProcessor()
    p.set_blacklist({"nike", "coca cola", "disney"})
    return p


# ═══════════════════════════════════════
# _clean
# ═══════════════════════════════════════

class TestClean:

    def test_strips_whitespace(self, processor):
        result = processor._clean(["  sunset  ", "  beach  "])
        assert result == ["sunset", "beach"]

    def test_strips_quotes(self, processor):
        result = processor._clean(['"sunset"', "'beach'"])
        assert result == ["sunset", "beach"]

    def test_removes_empty(self, processor):
        result = processor._clean(["", "  ", "sunset"])
        assert result == ["sunset"]

    def test_removes_short_keywords(self, processor):
        """Keywords shorter than 2 chars are removed."""
        result = processor._clean(["a", "ok", "sunset"])
        assert result == ["ok", "sunset"]

    def test_removes_leading_trailing_punctuation(self, processor):
        result = processor._clean(["...sunset...", "---beach---"])
        assert result == ["sunset", "beach"]

    def test_collapses_internal_whitespace(self, processor):
        result = processor._clean(["golden   hour   sunset"])
        assert result == ["golden hour sunset"]

    def test_skips_non_string(self, processor):
        result = processor._clean([123, None, "sunset", True])
        assert result == ["sunset"]


# ═══════════════════════════════════════
# _dedup_case_insensitive
# ═══════════════════════════════════════

class TestDedupCaseInsensitive:

    def test_removes_duplicates(self, processor):
        result = processor._dedup_case_insensitive(["Sunset", "sunset", "SUNSET"])
        assert result == ["Sunset"]

    def test_preserves_first_occurrence(self, processor):
        result = processor._dedup_case_insensitive(["beach", "Beach", "BEACH"])
        assert result == ["beach"]

    def test_no_duplicates(self, processor):
        result = processor._dedup_case_insensitive(["sunset", "beach", "ocean"])
        assert result == ["sunset", "beach", "ocean"]

    def test_empty_list(self, processor):
        assert processor._dedup_case_insensitive([]) == []


# ═══════════════════════════════════════
# _stem_dedup
# ═══════════════════════════════════════

class TestStemDedup:

    def test_dedup_by_stem(self, processor):
        """'running' and 'run' should collapse to the shorter form."""
        result = processor._stem_dedup(["running", "run"])
        assert "run" in result
        assert len(result) == 1

    def test_irregular_map_applied(self, processor):
        """'women' → 'woman' via IRREGULAR_MAP before stemming."""
        result = processor._stem_dedup(["women", "woman"])
        assert len(result) == 1
        assert "woman" in result

    def test_generic_blacklist_filtered(self, processor):
        """Words in GENERIC_BLACKLIST are skipped."""
        result = processor._stem_dedup(["sunset", "image", "photo"])
        assert "sunset" in result
        assert "image" not in result
        assert "photo" not in result

    def test_keeps_shortest_form(self, processor):
        """Among 'walk', 'walked', 'walking' — keeps 'walk'."""
        result = processor._stem_dedup(["walking", "walked", "walk"])
        assert "walk" in result
        assert len(result) == 1

    def test_empty_list(self, processor):
        assert processor._stem_dedup([]) == []

    def test_fallback_without_nltk(self, processor):
        """If NLTK is unavailable, falls back to case-insensitive dedup."""
        with patch("core.logic.keyword_processor._get_stemmer", return_value=None):
            result = processor._stem_dedup(["sunset", "Sunset", "beach"])
            assert len(result) == 2


# ═══════════════════════════════════════
# _filter_blacklist
# ═══════════════════════════════════════

class TestFilterBlacklist:

    def test_no_blacklist_returns_all(self, processor):
        keywords = ["sunset", "beach", "ocean"]
        assert processor._filter_blacklist(keywords) == keywords

    def test_filters_exact_match(self, processor_with_blacklist):
        keywords = ["sunset", "nike", "beach"]
        result = processor_with_blacklist._filter_blacklist(keywords)
        assert "nike" not in result
        assert "sunset" in result

    def test_filters_phrase_match(self, processor_with_blacklist):
        keywords = ["sunset", "coca cola drink", "beach"]
        result = processor_with_blacklist._filter_blacklist(keywords)
        assert len(result) == 2
        assert "coca cola drink" not in result

    def test_word_boundary_matching(self, processor_with_blacklist):
        """'nike' should match 'nike shoes' but not 'snikers'."""
        keywords = ["nike shoes", "snikers", "beach"]
        result = processor_with_blacklist._filter_blacklist(keywords)
        assert "nike shoes" not in result
        assert "snikers" in result  # no word boundary match

    def test_case_insensitive(self, processor_with_blacklist):
        keywords = ["NIKE", "Nike Shoes", "beach"]
        result = processor_with_blacklist._filter_blacklist(keywords)
        assert "NIKE" not in result
        assert "Nike Shoes" not in result


# ═══════════════════════════════════════
# process_istock
# ═══════════════════════════════════════

class TestProcessIstock:

    def test_basic_pipeline(self, processor):
        keywords = ["Sunset", "sunset", "Beach", "Ocean", "  sky  "]
        result = processor.process_istock(keywords)
        assert "Sunset" in result
        assert result.count("Sunset") == 1  # deduped

    def test_preserves_phrases(self, processor):
        keywords = ["Golden Hour Sunset", "beach view", "ocean"]
        result = processor.process_istock(keywords)
        assert "Golden Hour Sunset" in result

    def test_respects_max_count(self, processor):
        keywords = [f"keyword_{i}" for i in range(100)]
        result = processor.process_istock(keywords, max_count=10)
        assert len(result) <= 10

    def test_with_blacklist(self, processor_with_blacklist):
        keywords = ["sunset", "nike shoes", "beach", "disney world"]
        result = processor_with_blacklist.process_istock(keywords)
        assert "nike shoes" not in result
        assert "disney world" not in result
        assert "sunset" in result


# ═══════════════════════════════════════
# process_hybrid
# ═══════════════════════════════════════

class TestProcessHybrid:

    def test_phrases_come_first(self, processor):
        keywords = ["sunset", "golden hour sunset", "beach"]
        result = processor.process_hybrid(keywords)
        # Phrases should appear before singles
        phrase_idx = None
        for i, kw in enumerate(result):
            if " " in kw:
                phrase_idx = i
                break
        if phrase_idx is not None:
            assert phrase_idx == 0

    def test_phrases_title_cased(self, processor):
        keywords = ["golden hour sunset", "beach view"]
        result = processor.process_hybrid(keywords)
        for kw in result:
            if " " in kw:
                assert kw == kw.title()

    def test_singles_stem_deduped(self, processor):
        keywords = ["running", "run", "sunset"]
        result = processor.process_hybrid(keywords)
        # Should not have both 'running' and 'run'
        lower_result = [r.lower() for r in result]
        assert not ("running" in lower_result and "run" in lower_result)

    def test_respects_max_count(self, processor):
        keywords = [f"keyword {i}" for i in range(30)] + [f"word{i}" for i in range(30)]
        result = processor.process_hybrid(keywords, max_count=20)
        assert len(result) <= 20

    def test_dedup_phrases_case_insensitive(self, processor):
        keywords = ["Golden Hour", "golden hour", "GOLDEN HOUR"]
        result = processor.process_hybrid(keywords)
        # Should only have one version
        lower_results = [r.lower() for r in result]
        assert lower_results.count("golden hour") == 1


# ═══════════════════════════════════════
# process_single
# ═══════════════════════════════════════

class TestProcessSingle:

    def test_explodes_phrases(self, processor):
        keywords = ["golden hour sunset"]
        result = processor.process_single(keywords)
        # Should be individual words
        for kw in result:
            assert " " not in kw

    def test_stem_dedup(self, processor):
        keywords = ["running fast", "run quickly"]
        result = processor.process_single(keywords)
        lower_result = [r.lower() for r in result]
        # 'running' and 'run' should collapse
        assert not ("running" in lower_result and "run" in lower_result)

    def test_filters_short_words(self, processor):
        keywords = ["a big sunset"]
        result = processor.process_single(keywords)
        assert "a" not in result  # too short (< 2 chars)

    def test_respects_max_count(self, processor):
        keywords = [" ".join(f"word{i}" for i in range(100))]
        result = processor.process_single(keywords, max_count=10)
        assert len(result) <= 10

    def test_with_blacklist(self, processor_with_blacklist):
        keywords = ["nike shoes sunset beach"]
        result = processor_with_blacklist.process_single(keywords)
        assert "nike" not in [r.lower() for r in result]


# ═══════════════════════════════════════
# set_blacklist
# ═══════════════════════════════════════

class TestSetBlacklist:

    def test_set_blacklist_lowercases(self, processor):
        processor.set_blacklist({"Nike", "DISNEY", "  Coca Cola  "})
        assert "nike" in processor._blacklist
        assert "disney" in processor._blacklist
        assert "coca cola" in processor._blacklist

    def test_set_blacklist_ignores_empty(self, processor):
        processor.set_blacklist({"", "  ", "nike"})
        assert "" not in processor._blacklist
        assert "nike" in processor._blacklist
