"""Pattern matching module for detecting sensitive data in text."""

import re
from dataclasses import dataclass
from typing import List, Optional

from .loader import SensitiveDataLoader


@dataclass
class Match:
    """Represents a match found in text."""

    value: str
    start: int
    end: int
    match_type: str


class PatternMatcher:
    """Finds sensitive data patterns in text using regex and exact matching."""

    # Built-in regex patterns for common PII types
    PATTERNS = {
        "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "phone": r"\d{3}[-]\d{4}|\d{3}[-]\d{3}[-]\d{4}|\(\d{3}\)\s*\d{3}[-]\d{4}|\+\d{1}[-]\d{3}[-]\d{3}[-]\d{4}",
        "ssn": r"\d{3}-\d{2}-\d{4}",
        "api_key": r"sk-[a-zA-Z0-9-]{20,}",
    }

    def __init__(self, sensitive_loader: Optional[SensitiveDataLoader] = None) -> None:
        self.sensitive_loader = sensitive_loader
        self.compiled_patterns = {
            name: re.compile(pattern) for name, pattern in self.PATTERNS.items()
        }

    def find_all(self, text: str) -> List[Match]:
        """Find all sensitive values in the given text.

        Priority: Exact string matches (highest) > Regex pattern matches
        """
        matches: List[Match] = []

        # Exact matches from loaded sensitive data (highest priority)
        if self.sensitive_loader:
            for category, values in self.sensitive_loader.data.items():
                for value in values:
                    # Use word boundary for exact matching
                    escaped = re.escape(value)
                    pattern = re.compile(escaped, re.IGNORECASE)
                    for m in pattern.finditer(text):
                        matches.append(
                            Match(
                                value=m.group(),
                                start=m.start(),
                                end=m.end(),
                                match_type=category,
                            )
                        )

        # Regex pattern matches for built-in PII types
        for pattern_name, pattern in self.compiled_patterns.items():
            for m in pattern.finditer(text):
                # Skip if already matched (overlapping)
                if not self._is_overlapping(m.start(), m.end(), matches):
                    matches.append(
                        Match(
                            value=m.group(),
                            start=m.start(),
                            end=m.end(),
                            match_type=pattern_name,
                        )
                    )

        # Sort by start position
        matches.sort(key=lambda x: x.start)

        # Resolve overlaps (keep longest matches)
        return self._resolve_overlaps(matches)

    def _is_overlapping(
        self, start: int, end: int, matches: List[Match]
    ) -> bool:
        """Check if a range overlaps with any existing matches."""
        for m in matches:
            if not (end <= m.start or start >= m.end):
                return True
        return False

    def _resolve_overlaps(self, matches: List[Match]) -> List[Match]:
        """Resolve overlapping matches by keeping the longest ones."""
        if not matches:
            return matches

        result = [matches[0]]
        for current in matches[1:]:
            prev = result[-1]
            if current.start < prev.end:
                # Overlapping - keep longer match
                if (current.end - current.start) > (prev.end - prev.start):
                    result[-1] = current
            else:
                result.append(current)
        return result