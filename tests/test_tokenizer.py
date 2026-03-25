import pytest
from src.tokenizer import Tokenizer, TokenizationResult
from src.store import TokenStore
from src.loader import SensitiveDataLoader
import tempfile
import json
import os


@pytest.fixture
def tokenizer(tmp_path):
    data = {"email": ["alice@email.com"], "phone": ["555-0123"]}
    data_file = tmp_path / "sensitive.json"
    data_file.write_text(json.dumps(data))
    loader = SensitiveDataLoader(str(data_file))
    return Tokenizer(loader)


def test_tokenize_single_email(tokenizer):
    store = TokenStore()
    result = tokenizer.tokenize_text("Contact alice@email.com", store)
    assert "alice@email.com" not in result.text
    assert "[TOKEN_EMAIL_1]" in result.text
    assert result.tokens_created == 1


def test_tokenize_multiple_values(tokenizer):
    store = TokenStore()
    result = tokenizer.tokenize_text("Email alice@email.com or call 555-0123", store)
    assert "alice@email.com" not in result.text
    assert "555-0123" not in result.text
    assert result.tokens_created == 2


def test_tokenize_messages(tokenizer):
    store = TokenStore()
    messages = [
        {"role": "user", "content": "Email alice@email.com"},
        {"role": "assistant", "content": "Got it"}
    ]
    result = tokenizer.tokenize_messages(messages, store)
    assert "[TOKEN_EMAIL_1]" in result[0]["content"]
    assert result[1]["content"] == "Got it"  # No change


def test_no_sensitive_data(tokenizer):
    store = TokenStore()
    result = tokenizer.tokenize_text("Hello world", store)
    assert result.text == "Hello world"
    assert result.tokens_created == 0


def test_duplicate_values_same_token(tokenizer):
    store = TokenStore()
    result = tokenizer.tokenize_text("alice@email.com and alice@email.com", store)
    assert result.tokens_created == 1
    # Both occurrences should be replaced with same token
    assert result.text.count("[TOKEN_EMAIL_1]") == 2


def test_tokenize_returns_mappings(tokenizer):
    store = TokenStore()
    result = tokenizer.tokenize_text("Contact alice@email.com", store)
    assert len(result.mappings) == 1
    assert "[TOKEN_EMAIL_1]" in result.mappings
    assert result.mappings["[TOKEN_EMAIL_1]"] == "alice@email.com"