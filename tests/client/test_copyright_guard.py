"""
Tests for client/core/logic/copyright_guard.py
Covers: initialize, is_blacklisted, filter_keywords, check_text, clean_text,
        scan_result, clear, word-boundary matching.
"""
import pytest

from core.logic.copyright_guard import CopyrightGuard


@pytest.fixture
def guard():
    g = CopyrightGuard()
    g.initialize(["nike", "coca cola", "disney", "marvel"])
    return g


@pytest.fixture
def empty_guard():
    return CopyrightGuard()


# ═══════════════════════════════════════
# Initialization
# ═══════════════════════════════════════

class TestInitialization:

    def test_initialize_sets_blacklist(self, guard):
        assert guard.is_initialized is True
        assert guard.word_count == 4

    def test_empty_guard_not_initialized(self, empty_guard):
        assert empty_guard.is_initialized is False
        assert empty_guard.word_count == 0

    def test_initialize_lowercases(self):
        g = CopyrightGuard()
        g.initialize(["NIKE", "Disney", "  Coca Cola  "])
        assert g.is_blacklisted("nike")
        assert g.is_blacklisted("disney")
        assert g.is_blacklisted("coca cola")

    def test_initialize_strips_whitespace(self):
        g = CopyrightGuard()
        g.initialize(["  nike  ", "  disney  "])
        assert g.word_count == 2

    def test_initialize_ignores_empty_strings(self):
        g = CopyrightGuard()
        g.initialize(["nike", "", "  ", "disney"])
        assert g.word_count == 2

    def test_clear(self, guard):
        guard.clear()
        assert guard.is_initialized is False
        assert guard.word_count == 0


# ═══════════════════════════════════════
# is_blacklisted
# ═══════════════════════════════════════

class TestIsBlacklisted:

    def test_exact_match(self, guard):
        assert guard.is_blacklisted("nike") is True

    def test_case_insensitive(self, guard):
        assert guard.is_blacklisted("NIKE") is True
        assert guard.is_blacklisted("Nike") is True

    def test_phrase_match(self, guard):
        assert guard.is_blacklisted("coca cola") is True

    def test_not_blacklisted(self, guard):
        assert guard.is_blacklisted("sunset") is False

    def test_partial_word_not_blacklisted(self, guard):
        """'nike' is blacklisted but 'snikers' should not be."""
        assert guard.is_blacklisted("snikers") is False

    def test_empty_string(self, guard):
        assert guard.is_blacklisted("") is False

    def test_empty_guard(self, empty_guard):
        assert empty_guard.is_blacklisted("nike") is False


# ═══════════════════════════════════════
# filter_keywords
# ═══════════════════════════════════════

class TestFilterKeywords:

    def test_removes_blacklisted(self, guard):
        keywords = ["sunset", "nike shoes", "beach", "disney world"]
        result = guard.filter_keywords(keywords)
        assert "sunset" in result
        assert "beach" in result
        assert "nike shoes" not in result
        assert "disney world" not in result

    def test_word_boundary_matching(self, guard):
        """'nike' in 'nike shoes' should match, but not in 'snikers'."""
        keywords = ["nike shoes", "snikers", "beach"]
        result = guard.filter_keywords(keywords)
        assert "nike shoes" not in result
        assert "snikers" in result

    def test_empty_blacklist_returns_all(self, empty_guard):
        keywords = ["nike", "disney", "sunset"]
        result = empty_guard.filter_keywords(keywords)
        assert result == keywords

    def test_empty_keywords(self, guard):
        assert guard.filter_keywords([]) == []

    def test_multi_word_blacklist_match(self, guard):
        keywords = ["enjoy coca cola drink", "sunset"]
        result = guard.filter_keywords(keywords)
        assert "enjoy coca cola drink" not in result
        assert "sunset" in result


# ═══════════════════════════════════════
# check_text
# ═══════════════════════════════════════

class TestCheckText:

    def test_finds_blacklisted_in_text(self, guard):
        found = guard.check_text("I love nike shoes and disney movies")
        assert len(found) >= 2

    def test_no_blacklisted_in_text(self, guard):
        found = guard.check_text("Beautiful sunset over the ocean")
        assert found == []

    def test_empty_text(self, guard):
        assert guard.check_text("") == []

    def test_empty_blacklist(self, empty_guard):
        assert empty_guard.check_text("nike disney") == []

    def test_case_insensitive_matching(self, guard):
        found = guard.check_text("NIKE is a brand")
        assert len(found) >= 1


# ═══════════════════════════════════════
# clean_text
# ═══════════════════════════════════════

class TestCleanText:

    def test_replaces_blacklisted_with_asterisks(self, guard):
        cleaned, removed = guard.clean_text("I love nike shoes")
        assert "nike" not in cleaned.lower()
        assert "***" in cleaned
        assert len(removed) >= 1

    def test_no_blacklisted_returns_original(self, guard):
        text = "Beautiful sunset over the ocean"
        cleaned, removed = guard.clean_text(text)
        assert cleaned == text
        assert removed == []

    def test_empty_text(self, guard):
        cleaned, removed = guard.clean_text("")
        assert cleaned == ""
        assert removed == []

    def test_empty_blacklist(self, empty_guard):
        text = "nike disney"
        cleaned, removed = empty_guard.clean_text(text)
        assert cleaned == text
        assert removed == []

    def test_multiple_replacements(self, guard):
        cleaned, removed = guard.clean_text("nike and disney and marvel")
        assert "nike" not in cleaned.lower()
        assert "disney" not in cleaned.lower()
        assert "marvel" not in cleaned.lower()
        assert len(removed) == 3

    def test_cleans_extra_spaces(self, guard):
        cleaned, _ = guard.clean_text("big  nike  shoes")
        assert "  " not in cleaned  # extra spaces collapsed


# ═══════════════════════════════════════
# scan_result
# ═══════════════════════════════════════

class TestScanResult:

    def test_finds_violations_in_title(self, guard):
        result = {"title": "Nike Running Shoes", "description": "Great shoes", "keywords": ["running"]}
        violations = guard.scan_result(result)
        assert "title" in violations

    def test_finds_violations_in_description(self, guard):
        result = {"title": "Running Shoes", "description": "Like disney magic", "keywords": ["running"]}
        violations = guard.scan_result(result)
        assert "description" in violations

    def test_finds_violations_in_keywords(self, guard):
        result = {"title": "Shoes", "description": "Great", "keywords": ["nike shoes", "running"]}
        violations = guard.scan_result(result)
        assert "keywords" in violations
        assert "nike shoes" in violations["keywords"]

    def test_no_violations(self, guard):
        result = {"title": "Sunset Beach", "description": "Beautiful view", "keywords": ["sunset", "beach"]}
        violations = guard.scan_result(result)
        assert violations == {}

    def test_empty_result(self, guard):
        violations = guard.scan_result({})
        assert violations == {}

    def test_violations_in_all_fields(self, guard):
        result = {
            "title": "Nike Sunset",
            "description": "Disney magic coca cola",
            "keywords": ["marvel heroes", "sunset"],
        }
        violations = guard.scan_result(result)
        assert "title" in violations
        assert "description" in violations
        assert "keywords" in violations
