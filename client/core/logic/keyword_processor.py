"""
BigEye Pro — Keyword Processor (Task B-07)
Handles keyword cleaning, deduplication, stemming, and blacklist filtering.
Supports 3 styles: iStock (keep phrases), Hybrid (phrase + single), Single words.
Uses NLTK Lancaster stemmer for aggressive stem-based dedup.
"""
import re
import logging
from typing import List, Set

logger = logging.getLogger("bigeye")

# ── NLTK setup (lazy load) ──
_stemmer = None

def _get_stemmer():
    """Lazy-load Lancaster stemmer."""
    global _stemmer
    if _stemmer is None:
        try:
            from nltk.stem import LancasterStemmer
            _stemmer = LancasterStemmer()
        except ImportError:
            logger.warning("NLTK not available, stemming disabled")
            _stemmer = None
    return _stemmer


# ═══════════════════════════════════════
# Irregular words (stem → preferred form)
# ═══════════════════════════════════════

IRREGULAR_WORDS = {
    "wom": "women", "man": "men", "child": "children",
    "person": "people", "foot": "feet", "tooth": "teeth",
    "goose": "geese", "mouse": "mice", "ox": "oxen",
    "leav": "leaves", "lif": "life", "knif": "knife",
    "wif": "wife", "shelv": "shelf", "cact": "cactus",
    "analys": "analysis", "dat": "data", "medium": "media",
    "octop": "octopus", "rad": "radius", "alumn": "alumni",
    "fungus": "fungi", "syllab": "syllabus",
}


class KeywordProcessor:
    """Post-processes AI-generated keywords based on platform rules."""

    def __init__(self):
        self._blacklist: Set[str] = set()

    def set_blacklist(self, words: set):
        """Set blacklisted words (lowercase)."""
        self._blacklist = {w.lower().strip() for w in words if w.strip()}

    # ── Public pipelines ──

    def process_istock(self, keywords: list, max_count: int = 45) -> list:
        """
        iStock pipeline: clean → case-insensitive dedup → blacklist → trim.
        Keeps original phrases (multi-word allowed).
        """
        cleaned = self._clean(keywords)
        deduped = self._dedup_case_insensitive(cleaned)
        filtered = self._filter_blacklist(deduped)
        return filtered[:max_count]

    def process_hybrid(self, keywords: list, max_count: int = 45) -> list:
        """
        Hybrid pipeline (matches Streamlit finalize_keywords_v5_ai_driven):
        - Preserve phrases as-is (Title Case)
        - Stem-dedup single words (keep shortest form)
        - Order: phrases first, then unique single words
        - Does NOT explode phrases into single words
        """
        cleaned = self._clean(keywords)

        # Separate phrases and singles
        phrases = []
        singles = []
        seen_phrases = set()

        for kw in cleaned:
            kw_lower = kw.lower()
            if " " in kw:
                if kw_lower not in seen_phrases:
                    seen_phrases.add(kw_lower)
                    phrases.append(kw.title())
            else:
                singles.append(kw)

        # Stem-dedup singles (keep shortest surface form per stem)
        unique_singles = self._stem_dedup(singles)

        # Combine: phrases first, then fill with unique single words
        result = list(phrases)
        seen_lower = {p.lower() for p in result}
        for s in unique_singles:
            if s.lower() not in seen_lower:
                result.append(s.title())
                seen_lower.add(s.lower())

        filtered = self._filter_blacklist(result)
        return filtered[:max_count]

    def process_single(self, keywords: list, max_count: int = 45) -> list:
        """
        Single words pipeline: explode all → stem dedup (keep shortest) → blacklist → trim.
        All multi-word keywords are split into individual words.
        """
        cleaned = self._clean(keywords)

        # Explode everything into single words
        singles = []
        for kw in cleaned:
            for word in kw.split():
                w = word.strip()
                if len(w) >= 2:
                    singles.append(w)

        deduped = self._stem_dedup(singles)
        filtered = self._filter_blacklist(deduped)
        return filtered[:max_count]

    # ── Internal helpers ──

    def _clean(self, keywords: list) -> list:
        """Clean keywords: strip, remove empty, remove non-alpha junk."""
        result = []
        for kw in keywords:
            if not isinstance(kw, str):
                continue
            # Strip whitespace and quotes
            kw = kw.strip().strip('"').strip("'").strip()
            # Remove leading/trailing punctuation (keep internal hyphens/spaces)
            kw = re.sub(r'^[^\w]+|[^\w]+$', '', kw)
            # Collapse internal whitespace
            kw = re.sub(r'\s+', ' ', kw).strip()
            if kw and len(kw) >= 2:
                result.append(kw)
        return result

    def _dedup_case_insensitive(self, keywords: list) -> list:
        """Remove duplicates case-insensitively, keeping first occurrence."""
        seen = set()
        result = []
        for kw in keywords:
            key = kw.lower()
            if key not in seen:
                seen.add(key)
                result.append(kw)
        return result

    def _stem_dedup(self, words: list) -> list:
        """
        Stem-based deduplication: group words by stem, keep the shortest
        surface form in each group. Handles irregular plurals.
        """
        stemmer = _get_stemmer()
        if stemmer is None:
            # Fallback: simple case-insensitive dedup
            return self._dedup_case_insensitive(words)

        # stem → list of surface forms
        stem_groups: dict[str, list] = {}
        for word in words:
            w_lower = word.lower()
            stem = stemmer.stem(w_lower)

            # Check irregular words — override stem
            if stem in IRREGULAR_WORDS:
                preferred = IRREGULAR_WORDS[stem]
                stem = stemmer.stem(preferred)

            if stem not in stem_groups:
                stem_groups[stem] = []
            stem_groups[stem].append(word)

        # Pick shortest surface form per stem group
        result = []
        for stem, forms in stem_groups.items():
            # Deduplicate forms case-insensitively first
            unique_forms = {}
            for f in forms:
                key = f.lower()
                if key not in unique_forms or len(f) < len(unique_forms[key]):
                    unique_forms[key] = f

            # Pick the shortest
            best = min(unique_forms.values(), key=len)

            # Check irregular: if stem maps to a preferred form, use it
            if stem in IRREGULAR_WORDS:
                best = IRREGULAR_WORDS[stem]

            result.append(best)

        return result

    def _filter_blacklist(self, keywords: list) -> list:
        """Remove keywords that contain any blacklisted word."""
        if not self._blacklist:
            return keywords
        result = []
        for kw in keywords:
            kw_lower = kw.lower()
            # Check if any blacklisted word appears as a whole word in the keyword
            blocked = False
            for bw in self._blacklist:
                if re.search(r'\b' + re.escape(bw) + r'\b', kw_lower):
                    blocked = True
                    break
            if not blocked:
                result.append(kw)
        return result
