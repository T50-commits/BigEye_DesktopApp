"""
BigEye Pro — Copyright Guard (Task B-08)
Filters trademarked and blacklisted terms from metadata.
Supports single-word and multi-word blacklist entries with word-boundary matching.
"""
import re
import logging
from typing import List, Set, Tuple

logger = logging.getLogger("bigeye")


class CopyrightGuard:
    """Manages blacklist filtering for keywords, titles, and descriptions."""

    def __init__(self):
        self._blacklist: Set[str] = set()
        self._patterns: list = []  # Compiled regex patterns
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def word_count(self) -> int:
        return len(self._blacklist)

    def initialize(self, blacklist_words: list):
        """Load blacklist words and compile regex patterns."""
        self._blacklist = {w.lower().strip() for w in blacklist_words if w.strip()}
        # Compile patterns for word-boundary matching (sorted longest first)
        sorted_words = sorted(self._blacklist, key=len, reverse=True)
        self._patterns = [
            re.compile(r'\b' + re.escape(w) + r'\b', re.IGNORECASE)
            for w in sorted_words
        ]
        self._initialized = True
        logger.info("CopyrightGuard initialized")

    def is_blacklisted(self, word: str) -> bool:
        """Check if a single word/phrase is in the blacklist."""
        return word.lower().strip() in self._blacklist

    def filter_keywords(self, keywords: list) -> list:
        """Remove keywords that contain any blacklisted term."""
        if not self._blacklist:
            return keywords
        result = []
        for kw in keywords:
            if not self._contains_blacklisted(kw):
                result.append(kw)
        return result

    def check_text(self, text: str) -> List[str]:
        """
        Check a text (title or description) for blacklisted terms.
        Returns list of found blacklisted terms.
        """
        if not self._blacklist or not text:
            return []
        found = []
        for pattern in self._patterns:
            if pattern.search(text):
                found.append(pattern.pattern.replace(r'\b', '').replace('\\', ''))
        return found

    def clean_text(self, text: str) -> Tuple[str, List[str]]:
        """
        Remove blacklisted terms from text, replacing with '***'.
        Returns (cleaned_text, list_of_removed_terms).
        """
        if not self._blacklist or not text:
            return text, []
        removed = []
        cleaned = text
        for pattern in self._patterns:
            if pattern.search(cleaned):
                match_text = pattern.pattern.replace(r'\b', '').replace('\\', '')
                removed.append(match_text)
                cleaned = pattern.sub('***', cleaned)
        # Clean up multiple asterisks and extra spaces
        cleaned = re.sub(r'\*{3,}', '***', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned, removed

    def scan_result(self, result: dict) -> dict:
        """
        Scan a complete metadata result dict for blacklisted terms.
        Returns dict with found violations per field.
        E.g. {"title": ["nike"], "description": ["coca cola"], "keywords": ["disney"]}
        """
        violations = {}
        if "title" in result:
            found = self.check_text(result["title"])
            if found:
                violations["title"] = found
        if "description" in result:
            found = self.check_text(result["description"])
            if found:
                violations["description"] = found
        if "keywords" in result:
            kw_violations = []
            for kw in result["keywords"]:
                if self._contains_blacklisted(kw):
                    kw_violations.append(kw)
            if kw_violations:
                violations["keywords"] = kw_violations
        return violations

    def clear(self):
        """Clear blacklist data."""
        self._blacklist.clear()
        self._patterns.clear()
        self._initialized = False

    def _contains_blacklisted(self, text: str) -> bool:
        """Check if text contains any blacklisted term (word-boundary)."""
        if not text:
            return False
        for pattern in self._patterns:
            if pattern.search(text):
                return True
        return False
