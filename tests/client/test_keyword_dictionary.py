"""
Tests for keyword dictionary/processor logic:
  - IRREGULAR_MAP: surface form → base form mapping (women→woman, running→run)
  - GENERIC_BLACKLIST: filler words filtered out
  - _stem_dedup: stem-based deduplication keeping shortest form
  - _clean: strip, remove junk, collapse whitespace
  - _dedup_case_insensitive: case-insensitive dedup
  - _filter_blacklist: word-boundary matching
  - process_istock: keep phrases, case-insensitive dedup
  - process_hybrid: phrases first (Title Case), stem-dedup singles
  - process_single: explode all to single words, stem dedup
  - set_blacklist: server-provided blacklist
  - CopyrightGuard: blacklist filtering, text scanning, scan_result
"""
import pytest

from core.logic.keyword_processor import (
    KeywordProcessor, IRREGULAR_MAP, GENERIC_BLACKLIST,
)
from core.logic.copyright_guard import CopyrightGuard


# ═══════════════════════════════════════
# IRREGULAR_MAP
# ═══════════════════════════════════════

class TestIrregularMap:

    def test_women_to_woman(self):
        assert IRREGULAR_MAP["women"] == "woman"

    def test_men_to_man(self):
        assert IRREGULAR_MAP["men"] == "man"

    def test_children_to_child(self):
        assert IRREGULAR_MAP["children"] == "child"

    def test_people_to_person(self):
        assert IRREGULAR_MAP["people"] == "person"

    def test_running_to_run(self):
        assert IRREGULAR_MAP["running"] == "run"

    def test_smiling_to_smile(self):
        assert IRREGULAR_MAP["smiling"] == "smile"

    def test_better_to_good(self):
        assert IRREGULAR_MAP["better"] == "good"

    def test_best_to_good(self):
        assert IRREGULAR_MAP["best"] == "good"

    def test_all_keys_lowercase(self):
        for key in IRREGULAR_MAP:
            assert key == key.lower()

    def test_all_values_lowercase(self):
        for val in IRREGULAR_MAP.values():
            assert val == val.lower()


# ═══════════════════════════════════════
# GENERIC_BLACKLIST
# ═══════════════════════════════════════

class TestGenericBlacklist:

    def test_filler_words_present(self):
        for word in ["of", "the", "a", "an", "with", "in", "on", "at", "by"]:
            assert word in GENERIC_BLACKLIST

    def test_brand_names_present(self):
        for word in ["iphone", "samsung", "canon", "nikon"]:
            assert word in GENERIC_BLACKLIST

    def test_generic_photo_terms_present(self):
        for word in ["image", "photo", "picture", "shot", "concept", "background"]:
            assert word in GENERIC_BLACKLIST

    def test_social_media_present(self):
        for word in ["instagram", "tiktok", "facebook", "twitter", "youtube"]:
            assert word in GENERIC_BLACKLIST


# ═══════════════════════════════════════
# KeywordProcessor._clean
# ═══════════════════════════════════════

class TestClean:

    @pytest.fixture
    def kp(self):
        return KeywordProcessor()

    def test_strip_whitespace(self, kp):
        assert kp._clean(["  sunset  ", " ocean "]) == ["sunset", "ocean"]

    def test_strip_quotes(self, kp):
        assert kp._clean(['"sunset"', "'ocean'"]) == ["sunset", "ocean"]

    def test_remove_leading_trailing_punctuation(self, kp):
        assert kp._clean(["--sunset--", "...ocean..."]) == ["sunset", "ocean"]

    def test_collapse_internal_whitespace(self, kp):
        assert kp._clean(["golden   sunset"]) == ["golden sunset"]

    def test_remove_empty(self, kp):
        assert kp._clean(["", "  ", "a"]) == []  # "a" is len < 2

    def test_remove_single_char(self, kp):
        assert kp._clean(["x"]) == []

    def test_non_string_ignored(self, kp):
        assert kp._clean([123, None, "sunset"]) == ["sunset"]

    def test_keep_internal_hyphens(self, kp):
        result = kp._clean(["well-lit"])
        assert result == ["well-lit"]


# ═══════════════════════════════════════
# KeywordProcessor._stem_dedup
# ═══════════════════════════════════════

class TestStemDedup:

    @pytest.fixture
    def kp(self):
        return KeywordProcessor()

    def test_basic_dedup(self, kp):
        """'run' and 'running' should dedup to 'run' (shorter)."""
        result = kp._stem_dedup(["running", "run"])
        assert "run" in result
        assert len(result) == 1

    def test_irregular_map_applied(self, kp):
        """'women' should map to 'woman' before stemming."""
        result = kp._stem_dedup(["women", "woman"])
        assert len(result) == 1
        assert "woman" in result

    def test_keeps_shortest_form(self, kp):
        """Among 'walk', 'walking', 'walked' → keep 'walk'."""
        result = kp._stem_dedup(["walking", "walked", "walk"])
        assert "walk" in result
        assert len(result) == 1

    def test_generic_blacklist_filtered(self, kp):
        """Words in GENERIC_BLACKLIST should be removed."""
        result = kp._stem_dedup(["sunset", "image", "photo", "ocean"])
        assert "image" not in result
        assert "photo" not in result
        assert "sunset" in result
        assert "ocean" in result

    def test_different_stems_kept(self, kp):
        result = kp._stem_dedup(["sunset", "mountain", "ocean"])
        assert len(result) == 3

    def test_empty_input(self, kp):
        assert kp._stem_dedup([]) == []


# ═══════════════════════════════════════
# KeywordProcessor._filter_blacklist
# ═══════════════════════════════════════

class TestFilterBlacklist:

    @pytest.fixture
    def kp(self):
        p = KeywordProcessor()
        p.set_blacklist({"nike", "coca cola", "disney"})
        return p

    def test_removes_exact_match(self, kp):
        result = kp._filter_blacklist(["sunset", "nike", "ocean"])
        assert "nike" not in result
        assert "sunset" in result

    def test_removes_phrase_match(self, kp):
        result = kp._filter_blacklist(["sunset", "coca cola bottle", "ocean"])
        assert "coca cola bottle" not in result

    def test_word_boundary_matching(self, kp):
        """'nike' should match 'nike shoes' but not 'turnike'."""
        result = kp._filter_blacklist(["nike shoes", "turnike", "sunset"])
        assert "nike shoes" not in result
        assert "turnike" in result  # no word boundary match

    def test_case_insensitive(self, kp):
        result = kp._filter_blacklist(["NIKE", "Nike Shoes", "sunset"])
        assert "NIKE" not in result
        assert "Nike Shoes" not in result

    def test_no_blacklist_returns_all(self):
        kp = KeywordProcessor()  # no blacklist set
        result = kp._filter_blacklist(["nike", "sunset"])
        assert result == ["nike", "sunset"]

    def test_multi_word_blacklist(self, kp):
        result = kp._filter_blacklist(["coca cola", "pepsi", "coca"])
        assert "coca cola" not in result
        assert "pepsi" in result
        assert "coca" in result  # "coca" alone doesn't match "coca cola"


# ═══════════════════════════════════════
# process_istock
# ═══════════════════════════════════════

class TestProcessIstock:

    @pytest.fixture
    def kp(self):
        p = KeywordProcessor()
        p.set_blacklist({"nike"})
        return p

    def test_keeps_phrases(self, kp):
        result = kp.process_istock(["golden sunset", "calm ocean"], max_count=45)
        assert "golden sunset" in result
        assert "calm ocean" in result

    def test_case_insensitive_dedup(self, kp):
        result = kp.process_istock(["Sunset", "sunset", "SUNSET"], max_count=45)
        assert len(result) == 1

    def test_blacklist_applied(self, kp):
        result = kp.process_istock(["sunset", "nike shoes", "ocean"], max_count=45)
        assert "nike shoes" not in result

    def test_max_count_honored(self, kp):
        keywords = [f"keyword_{i}" for i in range(100)]
        result = kp.process_istock(keywords, max_count=10)
        assert len(result) <= 10

    def test_empty_input(self, kp):
        assert kp.process_istock([], max_count=45) == []


# ═══════════════════════════════════════
# process_hybrid
# ═══════════════════════════════════════

class TestProcessHybrid:

    @pytest.fixture
    def kp(self):
        return KeywordProcessor()

    def test_phrases_first_then_singles(self, kp):
        result = kp.process_hybrid(
            ["golden sunset", "ocean", "calm sea", "beach"],
            max_count=45,
        )
        # Phrases should come before singles
        phrase_indices = [i for i, kw in enumerate(result) if " " in kw]
        single_indices = [i for i, kw in enumerate(result) if " " not in kw]
        if phrase_indices and single_indices:
            assert max(phrase_indices) < min(single_indices)

    def test_phrases_title_cased(self, kp):
        result = kp.process_hybrid(["golden sunset", "calm ocean"], max_count=45)
        assert "Golden Sunset" in result
        assert "Calm Ocean" in result

    def test_singles_title_cased(self, kp):
        result = kp.process_hybrid(["sunset", "ocean"], max_count=45)
        for kw in result:
            if " " not in kw:
                assert kw == kw.title()

    def test_stem_dedup_singles(self, kp):
        """'running' and 'run' should dedup to one."""
        result = kp.process_hybrid(["running", "run", "sunset"], max_count=45)
        run_variants = [kw for kw in result if "run" in kw.lower()]
        assert len(run_variants) == 1

    def test_max_count(self, kp):
        keywords = [f"keyword {i}" for i in range(30)] + [f"word{i}" for i in range(30)]
        result = kp.process_hybrid(keywords, max_count=10)
        assert len(result) <= 10

    def test_phrase_dedup(self, kp):
        result = kp.process_hybrid(
            ["golden sunset", "Golden Sunset", "GOLDEN SUNSET"],
            max_count=45,
        )
        assert len(result) == 1


# ═══════════════════════════════════════
# process_single
# ═══════════════════════════════════════

class TestProcessSingle:

    @pytest.fixture
    def kp(self):
        p = KeywordProcessor()
        p.set_blacklist({"disney"})
        return p

    def test_explodes_phrases(self, kp):
        result = kp.process_single(["golden sunset over ocean"], max_count=45)
        assert "golden" in result
        assert "sunset" in result
        assert "ocean" in result
        # "over" is too short (len=4, but >=2 so included unless blacklisted)
        # Actually "over" is len 4 >= 2, so it's included

    def test_stem_dedup(self, kp):
        result = kp.process_single(["running fast", "run quickly"], max_count=45)
        run_variants = [kw for kw in result if "run" in kw.lower()]
        assert len(run_variants) == 1

    def test_blacklist_applied(self, kp):
        result = kp.process_single(["disney castle magic"], max_count=45)
        assert "disney" not in result
        assert "castle" in result

    def test_removes_single_char_words(self, kp):
        result = kp.process_single(["a big dog"], max_count=45)
        assert "a" not in result

    def test_max_count(self, kp):
        keywords = [f"word{i} extra{i}" for i in range(50)]
        result = kp.process_single(keywords, max_count=10)
        assert len(result) <= 10


# ═══════════════════════════════════════
# CopyrightGuard
# ═══════════════════════════════════════

class TestCopyrightGuard:

    @pytest.fixture
    def guard(self):
        g = CopyrightGuard()
        g.initialize(["nike", "coca cola", "disney", "marvel"])
        return g

    def test_is_initialized(self, guard):
        assert guard.is_initialized is True
        assert guard.word_count == 4

    def test_not_initialized_by_default(self):
        g = CopyrightGuard()
        assert g.is_initialized is False

    def test_is_blacklisted(self, guard):
        assert guard.is_blacklisted("nike") is True
        assert guard.is_blacklisted("Nike") is True
        assert guard.is_blacklisted("sunset") is False

    def test_filter_keywords(self, guard):
        result = guard.filter_keywords(["sunset", "nike shoes", "ocean", "disney castle"])
        assert "sunset" in result
        assert "ocean" in result
        assert "nike shoes" not in result
        assert "disney castle" not in result

    def test_check_text_finds_violations(self, guard):
        found = guard.check_text("I love Nike shoes and Disney movies")
        assert len(found) >= 2

    def test_check_text_no_violations(self, guard):
        found = guard.check_text("Beautiful sunset over the ocean")
        assert found == []

    def test_check_text_empty(self, guard):
        assert guard.check_text("") == []

    def test_clean_text_replaces_with_asterisks(self, guard):
        cleaned, removed = guard.clean_text("I love Nike shoes")
        assert "***" in cleaned
        assert len(removed) >= 1

    def test_clean_text_no_violations(self, guard):
        cleaned, removed = guard.clean_text("Beautiful sunset")
        assert cleaned == "Beautiful sunset"
        assert removed == []

    def test_scan_result_all_fields(self, guard):
        result = {
            "title": "Nike Running Shoes",
            "description": "Disney inspired coca cola themed shoes",
            "keywords": ["nike", "sunset", "disney castle", "ocean"],
        }
        violations = guard.scan_result(result)
        assert "title" in violations
        assert "description" in violations
        assert "keywords" in violations
        assert "nike" in violations["keywords"]
        assert "disney castle" in violations["keywords"]

    def test_scan_result_no_violations(self, guard):
        result = {
            "title": "Beautiful Sunset",
            "description": "Golden sunset over calm ocean",
            "keywords": ["sunset", "golden", "ocean"],
        }
        violations = guard.scan_result(result)
        assert violations == {}

    def test_clear(self, guard):
        guard.clear()
        assert guard.is_initialized is False
        assert guard.word_count == 0

    def test_multi_word_blacklist_boundary(self, guard):
        """'coca cola' should match as a phrase, not 'coca' alone."""
        result = guard.filter_keywords(["coca", "coca cola", "cola"])
        assert "coca" in result  # "coca" alone doesn't match "coca cola"
        assert "cola" in result
        assert "coca cola" not in result

    def test_word_boundary_prevents_partial(self, guard):
        """'nike' should not match inside 'turnike'."""
        result = guard.filter_keywords(["turnike", "nike"])
        assert "turnike" in result
        assert "nike" not in result
