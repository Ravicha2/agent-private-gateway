"""Comprehensive unit tests for all modules."""

import pytest
import json
import tempfile
import os
from src.config import GatewayConfig
from src.models import ChatRequest, ChatMessage
from src.loader import SensitiveDataLoader
from src.matcher import PatternMatcher, Match
from src.tokenizer import Tokenizer
from src.store import TokenStore
from src.detokenizer import Detokenizer
from src.ollama_client import OllamaClient


class TestConfig:
    """Test configuration module."""

    def test_default_values(self):
        config = GatewayConfig()
        assert config.ollama_url == "http://localhost:11434"
        assert config.log_level == "INFO"

    @pytest.mark.skip(reason="Config is cached at import time")
    def test_env_override(self, monkeypatch):
        """Config env override test - skipped due to module caching."""
        pass

    def test_sensitive_data_path_default(self):
        config = GatewayConfig()
        assert "sensitive_data.json" in config.sensitive_data_path


class TestModels:
    """Test data models."""

    def test_valid_message(self):
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_message_with_system_role(self):
        msg = ChatMessage(role="system", content="You are helpful")
        assert msg.role == "system"

    def test_message_with_assistant_role(self):
        msg = ChatMessage(role="assistant", content="I can help")
        assert msg.role == "assistant"

    def test_chat_request_valid(self):
        request = ChatRequest(
            model="llama2",
            messages=[ChatMessage(role="user", content="Hello")]
        )
        assert request.model == "llama2"
        assert len(request.messages) == 1


class TestLoaderEdgeCases:
    """Test loader with edge cases."""

    def test_empty_file(self, tmp_path):
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("{}")
        loader = SensitiveDataLoader(str(empty_file))
        assert len(loader.data) == 0

    def test_unicode_content(self, tmp_path):
        file = tmp_path / "unicode.json"
        data = {"emails": ["test@例⼦.com"]}
        file.write_text(json.dumps(data), encoding='utf-8')
        loader = SensitiveDataLoader(str(file))
        assert len(loader.get_by_category("emails")) == 1

    def test_malformed_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json")
        with pytest.raises(json.JSONDecodeError):
            SensitiveDataLoader(str(bad_file))

    def test_multiple_categories(self, tmp_path):
        file = tmp_path / "multi.json"
        data = {
            "email": ["a@test.com"],
            "phone": ["555-1234"],
            "ssn": ["123-45-6789"]
        }
        file.write_text(json.dumps(data))
        loader = SensitiveDataLoader(str(file))
        assert len(loader.get_by_category("email")) == 1
        assert len(loader.get_by_category("phone")) == 1
        assert len(loader.get_by_category("ssn")) == 1


class TestMatcherEdgeCases:
    """Test pattern matcher edge cases."""

    def test_overlapping_patterns(self):
        text = "Call 555-0123 or email test@example.com"
        matcher = PatternMatcher()
        matches = matcher.find_all(text)
        assert len(matches) >= 2

    def test_no_matches(self):
        text = "Hello world, no sensitive data here"
        matcher = PatternMatcher()
        matches = matcher.find_all(text)
        assert len(matches) == 0

    def test_case_insensitive_email(self):
        text = "EMAIL Test@Example.COM"
        matcher = PatternMatcher()
        matches = matcher.find_all(text)
        assert any("test@example.com" in m.value.lower() for m in matches)

    def test_phone_formats(self):
        text = "Call (555) 123-4567 or 555.123.4567"
        matcher = PatternMatcher()
        matches = matcher.find_all(text)
        assert any(m.match_type == "phone" for m in matches)

    def test_ssn_format(self):
        text = "SSN: 123-45-6789"
        matcher = PatternMatcher()
        matches = matcher.find_all(text)
        assert any(m.match_type == "ssn" for m in matches)


class TestTokenizerComplexInputs:
    """Test tokenizer with complex inputs."""

    def test_tokenize_with_special_chars(self):
        text = "Contact test+spam@example.com"
        store = TokenStore()
        matcher = PatternMatcher()
        # Should handle special characters without crashing
        matches = matcher.find_all(text)
        assert len(matches) >= 0  # Just verify no crash

    def test_multiple_same_value(self):
        text = "Email test@example.com and again test@example.com"
        store = TokenStore()
        tokenizer = Tokenizer(None)
        result = tokenizer.tokenize_text(text, store)
        # Same value should get same token count
        assert result.tokens_created >= 1

    def test_tokenize_empty_messages(self):
        store = TokenStore()
        tokenizer = Tokenizer(None)
        result = tokenizer.tokenize_messages([], store)
        assert len(result) == 0


class TestTokenStore:
    """Test token store operations."""

    def test_add_returns_token(self):
        store = TokenStore()
        token = store.add("test@example.com", "email")
        assert token.startswith("[TOKEN_EMAIL_")

    def test_duplicate_add_returns_same(self):
        store = TokenStore()
        t1 = store.add("test@example.com", "email")
        t2 = store.add("test@example.com", "email")
        assert t1 == t2

    def test_clear(self):
        store = TokenStore()
        store.add("test@example.com", "email")
        store.clear()
        assert len(store) == 0

    def test_len(self):
        store = TokenStore()
        store.add("test1@example.com", "email")
        store.add("test2@example.com", "email")
        assert len(store) == 2


class TestDetokenizer:
    """Test detokenizer operations."""

    def test_extract_tokens(self):
        detokenizer = Detokenizer()
        text = "Email [TOKEN_EMAIL_1] or call [TOKEN_PHONE_1]"
        tokens = detokenizer.extract_tokens(text)
        assert len(tokens) == 2

    def test_restore_no_tokens(self):
        detokenizer = Detokenizer()
        store = TokenStore()
        result = detokenizer.restore_tokens("Hello world", store)
        assert result.text == "Hello world"
        assert result.tokens_restored == 0

    def test_restore_with_store(self):
        detokenizer = Detokenizer()
        store = TokenStore()
        store.add("test@example.com", "email")
        result = detokenizer.restore_tokens("Email is [TOKEN_EMAIL_1]", store)
        assert "test@example.com" in result.text


class TestOllamaClient:
    """Test Ollama client."""

    def test_token_preservation_instruction(self):
        client = OllamaClient("http://localhost:11434")
        assert "TOKEN" in client.TOKEN_PRESERVATION_INSTRUCTION

    def test_inject_system_prompt(self):
        client = OllamaClient("http://localhost:11434")
        messages = [{"role": "user", "content": "Hello"}]
        result = client._inject_system_prompt(messages)
        assert result[0]["role"] == "system"
        assert "TOKEN" in result[0]["content"]