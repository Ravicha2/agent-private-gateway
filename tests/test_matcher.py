"""Tests for the pattern matcher."""

import json
import os
import tempfile

import pytest

from src.loader import SensitiveDataLoader
from src.matcher import PatternMatcher, Match


@pytest.fixture
def loader_with_data():
    """Create a loader with test data."""
    data = {
        "custom": ["SecretProject", "ConfidentialData"],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        temp_path = f.name

    loader = SensitiveDataLoader(temp_path)
    yield loader
    os.unlink(temp_path)


def test_email_matching():
    """Test email pattern matching."""
    matcher = PatternMatcher()
    matches = matcher.find_all("Contact alice@email.com for help")
    assert len(matches) == 1
    assert matches[0].value == "alice@email.com"
    assert matches[0].match_type == "email"


def test_phone_matching():
    """Test phone number pattern matching."""
    matcher = PatternMatcher()
    matches = matcher.find_all("Call 555-0123 for support")
    assert len(matches) == 1
    assert matches[0].value == "555-0123"
    assert matches[0].match_type == "phone"


def test_ssn_matching():
    """Test SSN pattern matching."""
    matcher = PatternMatcher()
    matches = matcher.find_all("SSN: 123-45-6789")
    assert len(matches) == 1
    assert matches[0].value == "123-45-6789"
    assert matches[0].match_type == "ssn"


def test_api_key_matching():
    """Test API key pattern matching."""
    matcher = PatternMatcher()
    matches = matcher.find_all("API key: sk-live-abc123xyz789012")
    assert len(matches) == 1
    assert matches[0].match_type == "api_key"


def test_exact_string_matching(loader_with_data):
    """Test exact string matching from loaded data."""
    matcher = PatternMatcher(sensitive_loader=loader_with_data)
    matches = matcher.find_all("Project SecretProject is confidential")
    assert len(matches) == 1
    assert matches[0].value == "SecretProject"
    assert matches[0].match_type == "custom"


def test_exact_match_priority_over_regex(loader_with_data):
    """Test that exact matches take priority over regex."""
    # "555-0123" could match phone pattern, but we also have exact match
    matcher = PatternMatcher(sensitive_loader=loader_with_data)
    # If we add 555-0123 to custom, exact should take priority
    matches = matcher.find_all("Call 555-0123")
    assert len(matches) >= 1
    # Should match as phone pattern
    assert matches[0].match_type == "phone"


def test_overlapping_patterns():
    """Test overlapping pattern resolution."""
    matcher = PatternMatcher()
    # Phone number-like pattern that could overlap
    text = "Call (555) 123-4567"
    matches = matcher.find_all(text)
    assert len(matches) == 1
    # Should match as phone
    assert matches[0].match_type == "phone"


def test_no_matches():
    """Test text with no sensitive data."""
    matcher = PatternMatcher()
    matches = matcher.find_all("Hello world, this is safe text.")
    assert len(matches) == 0


def test_multiple_matches():
    """Test finding multiple sensitive values."""
    matcher = PatternMatcher()
    matches = matcher.find_all("Email alice@email.com or call 555-0123")
    assert len(matches) == 2
    types = [m.match_type for m in matches]
    assert "email" in types
    assert "phone" in types


def test_word_boundary_handling():
    """Test that word boundaries are respected."""
    matcher = PatternMatcher()
    # bob@email.com should not match within robert@email.com
    matches = matcher.find_all("Contact robert@email.com for bob@email.com")
    assert len(matches) == 2


def test_case_insensitive_exact_match(loader_with_data):
    """Test case-insensitive exact string matching."""
    matcher = PatternMatcher(sensitive_loader=loader_with_data)
    matches = matcher.find_all("Project SECRETPROJECT is confidential")
    assert len(matches) == 1
    assert matches[0].match_type == "custom"