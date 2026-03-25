"""Tests for the sensitive data loader."""

import json
import os
import tempfile

import pytest

from src.loader import SensitiveDataLoader


@pytest.fixture
def sample_data_file():
    """Create a temporary sensitive data file."""
    data = {
        "emails": ["test@example.com", "alice@email.com"],
        "phones": ["555-0123", "+1-555-0199"],
        "custom": ["SecretProject"],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        temp_path = f.name
    yield temp_path
    os.unlink(temp_path)


def test_load_sensitive_data(sample_data_file):
    """Test loading valid JSON file."""
    loader = SensitiveDataLoader(sample_data_file)
    assert "test@example.com" in loader.get_by_category("emails")
    assert "alice@email.com" in loader.get_by_category("emails")
    assert "555-0123" in loader.get_by_category("phones")


def test_file_not_found():
    """Test FileNotFoundError when file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        SensitiveDataLoader("/nonexistent/path/data.json")


def test_get_by_category():
    """Test category retrieval."""
    data = {"emails": ["a@test.com"], "phones": ["123"]}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        temp_path = f.name

    try:
        loader = SensitiveDataLoader(temp_path)
        assert loader.get_by_category("emails") == ["a@test.com"]
        assert loader.get_by_category("phones") == ["123"]
        assert loader.get_by_category("nonexistent") == []
    finally:
        os.unlink(temp_path)


def test_is_sensitive_case_insensitive(sample_data_file):
    """Test case-insensitive sensitive check."""
    loader = SensitiveDataLoader(sample_data_file)
    assert loader.is_sensitive("TEST@EXAMPLE.COM") is True
    assert loader.is_sensitive("test@example.com") is True
    assert loader.is_sensitive("ALICE@EMAIL.COM") is True
    assert loader.is_sensitive("notsensitive@example.com") is False


def test_get_all_categories(sample_data_file):
    """Test getting all categories."""
    loader = SensitiveDataLoader(sample_data_file)
    categories = loader.get_all_categories()
    assert "emails" in categories
    assert "phones" in categories
    assert "custom" in categories