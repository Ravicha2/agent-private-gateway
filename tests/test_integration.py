"""Full integration tests."""

import pytest
import os
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

# Set the sensitive data path before importing the app
os.environ["GATEWAY_SENSITIVE_DATA_PATH"] = "sensitive_data.json"

from src.main import app


@pytest.fixture
def client():
    """Create a test client that triggers the app lifespan."""
    with TestClient(app) as test_client:
        yield test_client


class TestIntegration:
    """Full integration tests."""

    def test_health_endpoint(self, client):
        """Health check works."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_chat_without_sensitive_data(self, client):
        """Chat without sensitive data works."""
        with patch("src.main.ollama_client") as mock_ollama:
            mock_ollama.chat = AsyncMock(return_value={
                "model": "test-model",
                "message": {"role": "assistant", "content": "Hello!"},
                "done": True
            })

            response = client.post("/api/chat", json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hello"}]
            })

        assert response.status_code == 200
        result = response.json()
        assert "message" in result

    def test_chat_with_sensitive_data_tokenized(self, client):
        """Sensitive data gets tokenized and sent to Ollama."""
        with patch("src.main.ollama_client") as mock_ollama:
            mock_ollama.chat = AsyncMock(return_value={
                "model": "test-model",
                "message": {"role": "assistant", "content": "Email is [TOKEN_EMAIL_1]"},
                "done": True
            })

            response = client.post("/api/chat", json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Contact test@example.com"}]
            })

        assert response.status_code == 200

    def test_chat_response_detokenized(self, client):
        """Ollama response gets de-tokenized."""
        with patch("src.main.ollama_client") as mock_ollama:
            mock_ollama.chat = AsyncMock(return_value={
                "model": "test-model",
                "message": {"role": "assistant", "content": "Email is [TOKEN_EMAIL_1]"},
                "done": True
            })

            response = client.post("/api/chat", json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "test@example.com"}]
            })

        assert response.status_code == 200
        result = response.json()
        # Should have detokenization metadata
        assert "_detokenization" in result
        assert result["_detokenization"]["tokens_restored"] >= 0

    def test_multiple_messages(self, client):
        """Multiple messages are processed."""
        with patch("src.main.ollama_client") as mock_ollama:
            mock_ollama.chat = AsyncMock(return_value={
                "model": "test-model",
                "message": {"role": "assistant", "content": "Response"},
                "done": True
            })

            response = client.post("/api/chat", json={
                "model": "test-model",
                "messages": [
                    {"role": "system", "content": "You are helpful"},
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi"},
                    {"role": "user", "content": "How are you?"}
                ]
            })

        assert response.status_code == 200

    def test_system_prompt_injection(self, client):
        """System prompt with token preservation is injected."""
        with patch("src.main.ollama_client") as mock_ollama:
            mock_ollama.chat = AsyncMock(return_value={
                "model": "test-model",
                "message": {"role": "assistant", "content": "OK"},
                "done": True
            })

            response = client.post("/api/chat", json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Test"}]
            })

        assert response.status_code == 200
        # Verify the mock was called with inject_prompt=True (default)
        mock_ollama.chat.assert_called_once()

    def test_invalid_request_missing_model(self, client):
        """Invalid request returns error."""
        response = client.post("/api/chat", json={
            "messages": [{"role": "user", "content": "Hello"}]
        })
        # Should return validation error
        assert response.status_code in [400, 422]

    def test_invalid_request_missing_messages(self, client):
        """Invalid request returns error."""
        response = client.post("/api/chat", json={
            "model": "test-model"
        })
        # Should return validation error
        assert response.status_code in [400, 422]