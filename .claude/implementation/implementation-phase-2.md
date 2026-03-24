# Phase 2: Sensitive Data Loading & Pattern Matching

## Phase Status: 🔲 NOT STARTED

**Prerequisites**: [Phase 1 - Core Architecture](./implementation-phase-1.md) must be ✅ COMPLETED

**Next Phase**: [Phase 3 - Tokenization Engine](./implementation-phase-3.md)

---

## Phase Goal

Implement the ability to load sensitive data from JSON files and detect sensitive patterns in text using exact string matching and regex patterns.

---

## Implementation Steps

### Step 2.1: Create Sample Sensitive Data File

**Status**: 🔲 NOT STARTED

**File**: `sensitive_data.json` (at project root)

**Actions**:
- [ ] Create JSON file with test data
- [ ] Add email entries (test@example.com, alice@email.com)
- [ ] Add phone entries (555-0123, +1-555-0199)
- [ ] Add SSN entries (123-45-6789)
- [ ] Add custom sensitive strings

**Expected Output**:
```json
{
  "emails": ["test@example.com", "alice@email.com", "bob@company.org"],
  "phones": ["555-0123", "+1-555-0199", "(555) 555-5555"],
  "ssns": ["123-45-6789"],
  "api_keys": ["sk-live-abc123xyz"],
  "custom": ["SuperSecretProject", "ConfidentialData"]
}
```

---

### Step 2.2: Create Sensitive Data Loader

**Status**: 🔲 NOT STARTED

**File**: `src/loader.py`

**Actions**:
- [ ] Create SensitiveDataLoader class
- [ ] Add JSON file loading method
- [ ] Add validation for file existence
- [ ] Parse different data type categories
- [ ] Store data in normalized format (lowercase keys for case-insensitive matching)
- [ ] Add error handling for malformed JSON

**Expected Output**:
```python
# src/loader.py
import json
from pathlib import Path
from typing import Dict, List, Set

class SensitiveDataLoader:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.data: Dict[str, List[str]] = {}
        self.all_values: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Sensitive data file not found: {self.file_path}")

        with open(self.file_path, 'r') as f:
            self.data = json.load(f)

        # Normalize and collect all values
        for category, values in self.data.items():
            for value in values:
                self.all_values.add(value.lower())

    def get_by_category(self, category: str) -> List[str]:
        return self.data.get(category, [])

    def is_sensitive(self, value: str) -> bool:
        return value.lower() in self.all_values
```

---

### Step 2.3: Create Pattern Matcher

**Status**: 🔲 NOT STARTED

**File**: `src/matcher.py`

**Actions**:
- [ ] Create PatternMatcher class
- [ ] Define regex patterns for common PII types
- [ ] Add exact string matching from loaded data
- [ ] Implement find_all method that returns matches with positions
- [ ] Handle overlapping patterns (longest match first)
- [ ] Add word boundary checking

**Expected Output**:
```python
# src/matcher.py
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Match:
    value: str
    start: int
    end: int
    match_type: str

class PatternMatcher:
    PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone": r'\b(?:\+?1[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}\b',
        "ssn": r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b',
        "api_key": r'\bsk-[a-zA-Z0-9]{20,}\b',
    }

    def __init__(self, sensitive_loader=None):
        self.sensitive_loader = sensitive_loader
        self.compiled_patterns = {
            name: re.compile(pattern)
            for name, pattern in self.PATTERNS.items()
        }

    def find_all(self, text: str) -> List[Match]:
        """Find all sensitive values in text."""
        matches = []

        # Exact matches from loaded data (highest priority)
        if self.sensitive_loader:
            for category, values in self.sensitive_loader.data.items():
                for value in values:
                    pattern = re.compile(re.escape(value), re.IGNORECASE)
                    for m in pattern.finditer(text):
                        matches.append(Match(
                            value=m.group(),
                            start=m.start(),
                            end=m.end(),
                            match_type=category
                        ))

        # Regex pattern matches
        for pattern_name, pattern in self.compiled_patterns.items():
            for m in pattern.finditer(text):
                # Avoid duplicates (check if already matched by exact)
                if not self._is_overlapping(m.start(), m.end(), matches):
                    matches.append(Match(
                        value=m.group(),
                        start=m.start(),
                        end=m.end(),
                        match_type=pattern_name
                    ))

        # Sort by start position
        matches.sort(key=lambda x: x.start)

        # Resolve overlaps (keep longest matches)
        return self._resolve_overlaps(matches)

    def _is_overlapping(self, start: int, end: int, matches: List[Match]) -> bool:
        for m in matches:
            if not (end <= m.start or start >= m.end):
                return True
        return False

    def _resolve_overlaps(self, matches: List[Match]) -> List[Match]:
        if not matches:
            return matches

        result = [matches[0]]
        for current in matches[1:]:
            prev = result[-1]
            if current.start < prev.end:  # Overlapping
                # Keep longer match
                if (current.end - current.start) > (prev.end - prev.start):
                    result[-1] = current
            else:
                result.append(current)
        return result
```

---

### Step 2.4: Write Unit Tests for Loader

**Status**: 🔲 NOT STARTED

**File**: `tests/test_loader.py`

**Actions**:
- [ ] Test loading valid JSON file
- [ ] Test file not found error
- [ ] Test category retrieval
- [ ] Test is_sensitive check (case-insensitive)

**Expected Output**:
```python
# tests/test_loader.py
import pytest
import json
import tempfile
import os
from src.loader import SensitiveDataLoader

@pytest.fixture
def sample_data_file():
    data = {
        "emails": ["test@example.com"],
        "phones": ["555-0123"]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)

def test_load_sensitive_data(sample_data_file):
    loader = SensitiveDataLoader(sample_data_file)
    assert "test@example.com" in loader.get_by_category("emails")
    assert "555-0123" in loader.get_by_category("phones")

def test_is_sensitive_case_insensitive(sample_data_file):
    loader = SensitiveDataLoader(sample_data_file)
    assert loader.is_sensitive("TEST@EXAMPLE.COM")
    assert loader.is_sensitive("test@example.com")
```

---

### Step 2.5: Write Unit Tests for Matcher

**Status**: 🔲 NOT STARTED

**File**: `tests/test_matcher.py`

**Actions**:
- [ ] Test email pattern matching
- [ ] Test phone pattern matching
- [ ] Test exact string matching
- [ ] Test overlapping pattern resolution
- [ ] Test word boundary handling

**Expected Output**:
```python
# tests/test_matcher.py
import pytest
from src.matcher import PatternMatcher

def test_email_matching():
    matcher = PatternMatcher()
    matches = matcher.find_all("Contact alice@email.com for help")
    assert len(matches) == 1
    assert matches[0].value == "alice@email.com"
    assert matches[0].match_type == "email"

def test_overlapping_patterns():
    matcher = PatternMatcher()
    # Phone number could match SSN pattern too
    text = "Call 555-0123"
    matches = matcher.find_all(text)
    # Should keep the longest/best match
    assert len(matches) == 1
```

---

### Step 2.6: Integration Test

**Status**: 🔲 NOT STARTED

**Actions**:
- [ ] Create test using both loader and matcher together
- [ ] Verify exact matches take priority over regex
- [ ] Test with real-world text examples

---

## Completion Criteria

This phase is complete when:

- [ ] `sensitive_data.json` exists with test data
- [ ] `src/loader.py` loads and validates sensitive data
- [ ] `src/matcher.py` finds patterns in text
- [ ] Tests pass: `pytest tests/test_loader.py tests/test_matcher.py -v`
- [ ] Matcher handles overlapping patterns correctly
- [ ] Case-insensitive matching works

---

## Files Created/Modified in This Phase

1. `sensitive_data.json` - Sample sensitive data
2. `src/loader.py` - Data loading module
3. `src/matcher.py` - Pattern matching module
4. `tests/test_loader.py` - Loader tests
5. `tests/test_matcher.py` - Matcher tests

---

## After Completion

1. Update global-implementation.md: Set Phase 2 status to ✅ COMPLETED
2. Move to [Phase 3 - Tokenization Engine](./implementation-phase-3.md)
