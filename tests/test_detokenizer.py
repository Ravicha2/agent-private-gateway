"""Tests for Detokenizer."""

import pytest
from src.detokenizer import Detokenizer, DetokenizationResult
from src.store import TokenStore


def test_restore_exact_token():
    """Test exact token restoration."""
    store = TokenStore()
    store.add("alice@email.com", "email")

    detokenizer = Detokenizer()
    result = detokenizer.restore_tokens("Contact [TOKEN_EMAIL_1] please", store)

    assert result.text == "Contact alice@email.com please"
    assert result.tokens_restored == 1
    assert result.success is True


def test_fuzzy_match_lowercase():
    """Test fuzzy matching for lowercase tokens."""
    store = TokenStore()
    store.add("alice@email.com", "email")

    detokenizer = Detokenizer(fuzzy_match=True)
    result = detokenizer.restore_tokens("Contact [token_email_1] please", store)

    assert result.text == "Contact alice@email.com please"
    assert result.tokens_restored == 1


def test_fuzzy_match_disabled():
    """Test that fuzzy matching can be disabled."""
    store = TokenStore()
    store.add("alice@email.com", "email")

    detokenizer = Detokenizer(fuzzy_match=False)
    result = detokenizer.restore_tokens("Contact [token_email_1] please", store)

    # Should not match - lowercase token won't be found
    assert "[token_email_1]" in result.text
    assert result.tokens_restored == 0


def test_unmapped_token():
    """Test unmapped token handling."""
    store = TokenStore()
    # Don't add any tokens

    detokenizer = Detokenizer()
    result = detokenizer.restore_tokens("Contact [TOKEN_EMAIL_1] please", store)

    assert result.text == "Contact [TOKEN_EMAIL_1] please"  # Unchanged
    assert result.tokens_restored == 0
    assert "[TOKEN_EMAIL_1]" in result.unmapped_tokens
    assert result.success is False


def test_restore_chat_response():
    """Test chat response restoration."""
    store = TokenStore()
    store.add("alice@email.com", "email")

    detokenizer = Detokenizer()
    response = {
        "message": {"role": "assistant", "content": "Reach [TOKEN_EMAIL_1]"},
        "done": True
    }

    result = detokenizer.restore_chat_response(response, store)

    assert result["message"]["content"] == "Reach alice@email.com"
    assert result["_detokenization"]["tokens_restored"] == 1
    assert result["_detokenization"]["success"] is True


def test_multiple_tokens():
    """Test multiple tokens in text."""
    store = TokenStore()
    store.add("alice@email.com", "email")
    store.add("555-0123", "phone")

    detokenizer = Detokenizer()
    result = detokenizer.restore_tokens(
        "Email [TOKEN_EMAIL_1] or call [TOKEN_PHONE_1]",
        store
    )

    assert result.text == "Email alice@email.com or call 555-0123"
    assert result.tokens_restored == 2
    assert result.success is True


def test_no_tokens_in_text():
    """Test when there are no tokens in text."""
    store = TokenStore()
    store.add("alice@email.com", "email")

    detokenizer = Detokenizer()
    result = detokenizer.restore_tokens("Hello world", store)

    assert result.text == "Hello world"
    assert result.tokens_restored == 0
    assert result.success is True


def test_empty_store():
    """Test with empty store."""
    store = TokenStore()

    detokenizer = Detokenizer()
    result = detokenizer.restore_tokens("Contact [TOKEN_EMAIL_1]", store)

    # Should return unchanged text when store is empty
    assert result.text == "Contact [TOKEN_EMAIL_1]"
    assert result.tokens_restored == 0


def test_extract_tokens():
    """Test token extraction."""
    detokenizer = Detokenizer()
    text = "Email [TOKEN_EMAIL_1] or call [TOKEN_PHONE_1]"
    tokens = detokenizer.extract_tokens(text)

    assert len(tokens) == 2
    assert "[TOKEN_EMAIL_1]" in tokens
    assert "[TOKEN_PHONE_1]" in tokens


def test_restore_response_without_message():
    """Test restoring response without message field."""
    store = TokenStore()
    store.add("alice@email.com", "email")

    detokenizer = Detokenizer()
    response = {"done": True}

    result = detokenizer.restore_chat_response(response, store)
    assert result == response  # Unchanged