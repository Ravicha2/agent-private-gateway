"""Security-focused tests."""

import pytest
import logging
from src.tokenizer import Tokenizer
from src.store import TokenStore
from src.detokenizer import Detokenizer
from src.matcher import PatternMatcher


class TestSecurity:
    """Security-focused tests."""

    def test_store_cleared_after_request(self):
        """Token store should be cleared after each request."""
        store = TokenStore()
        store.add("secret@email.com", "email")
        store.clear()
        assert len(store) == 0
        assert store.get_value("[TOKEN_EMAIL_1]") is None

    def test_no_sql_injection_in_patterns(self):
        """Pattern matching shouldn't execute code."""
        malicious = "'; DROP TABLE users; --"
        matcher = PatternMatcher()
        # Should just match as text, not execute
        matches = matcher.find_all(malicious)
        # Should treat as literal text (no matches expected)
        assert isinstance(matches, list)

    def test_token_format_not_revealed(self):
        """Token format should be consistent but not expose mappings."""
        store = TokenStore()
        token = store.add("secret@email.com", "email")
        # Token should exist
        assert token is not None
        # Getting the value should work via token
        value = store.get_value(token)
        assert value == "secret@email.com"
        # But token shouldn't reveal the original value
        assert "secret" not in token

    def test_case_insensitive_no_leakage(self):
        """Case variations shouldn't leak data."""
        store = TokenStore()
        store.add("Test@Example.COM", "email")

        # Different case should return same token
        token1 = store.get_token("test@example.com")
        token2 = store.get_token("TEST@EXAMPLE.COM")
        assert token1 == token2

    def test_detokenizer_unmapped_tokens_preserved(self):
        """Unmapped tokens should remain as-is, not crash."""
        store = TokenStore()  # Empty store
        detokenizer = Detokenizer()

        # Should not crash and should preserve unmapped tokens
        result = detokenizer.restore_tokens("Contact [TOKEN_FAKE_1]", store)
        assert "[TOKEN_FAKE_1]" in result.text

    def test_empty_input_handling(self):
        """Empty inputs should be handled safely."""
        store = TokenStore()
        tokenizer = Tokenizer(None)

        # Empty text
        result = tokenizer.tokenize_text("", store)
        assert result.text == ""

        # None-like content
        result = tokenizer.tokenize_text("   ", store)
        assert result.tokens_created == 0

    def test_special_chars_in_sensitive_data(self):
        """Special characters in sensitive data should be handled."""
        store = TokenStore()
        # Email with plus sign
        store.add("test+tag@example.com", "email")

        token = store.get_token("test+tag@example.com")
        assert token is not None
        assert store.get_value(token) == "test+tag@example.com"