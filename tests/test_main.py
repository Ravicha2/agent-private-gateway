"""Tests for the main FastAPI application."""

import os
import pytest
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


def test_health(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_echo(client):
    """Test the chat endpoint forwards to Ollama and returns response."""
    payload = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "Hello"}],
    }

    # Mock the Ollama client response
    with patch("src.main.ollama_client") as mock_ollama:
        mock_ollama.chat = AsyncMock(return_value={
            "model": "test-model",
            "message": {"role": "assistant", "content": "Hello back!"},
            "done": True
        })
        response = client.post("/api/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["message"]["content"] == "Hello back!"


def test_chat_with_multiple_messages(client):
    """Test chat endpoint with multiple messages."""
    payload = {
        "model": "llama2",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ],
    }

    with patch("src.main.ollama_client") as mock_ollama:
        mock_ollama.chat = AsyncMock(return_value={
            "model": "llama2",
            "message": {"role": "assistant", "content": "Response"},
            "done": True
        })
        response = client.post("/api/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "llama2"