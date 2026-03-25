"""Tests for OllamaClient."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch
from src.ollama_client import OllamaClient


@pytest.fixture
def client():
    return OllamaClient("http://localhost:11434")


@pytest.mark.asyncio
async def test_chat_sends_request(client):
    """Test chat method sends correct payload to Ollama."""
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": {"content": "Hello"}}

    with patch.object(client.client, "post", return_value=mock_response) as mock_post:
        result = await client.chat("llama2", [{"role": "user", "content": "Hi"}])

        assert result["message"]["content"] == "Hello"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/chat"
        assert call_args[1]["json"]["model"] == "llama2"


@pytest.mark.asyncio
async def test_system_prompt_injection(client):
    """Test system prompt injection adds token preservation."""
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": {"content": "Hello"}}

    with patch.object(client.client, "post", return_value=mock_response):
        await client.chat("llama2", [{"role": "user", "content": "Hi [TOKEN_EMAIL_1]"}])

        call_args = client.client.post.call_args
        payload = call_args[1]["json"]
        assert payload["messages"][0]["role"] == "system"
        assert "TOKEN" in payload["messages"][0]["content"]


@pytest.mark.asyncio
async def test_system_prompt_injection_existing_system(client):
    """Test system prompt injection appends to existing system message."""
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": {"content": "Hello"}}

    with patch.object(client.client, "post", return_value=mock_response):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hi"}
        ]
        await client.chat("llama2", messages)

        call_args = client.client.post.call_args
        payload = call_args[1]["json"]
        assert payload["messages"][0]["role"] == "system"
        assert "You are a helpful assistant" in payload["messages"][0]["content"]
        assert "TOKEN" in payload["messages"][0]["content"]


@pytest.mark.asyncio
async def test_chat_no_injection_when_disabled(client):
    """Test chat without prompt injection."""
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"message": {"content": "Hello"}}

    with patch.object(client.client, "post", return_value=mock_response):
        await client.chat("llama2", [{"role": "user", "content": "Hi"}], inject_prompt=False)

        call_args = client.client.post.call_args
        payload = call_args[1]["json"]
        # Should only have user message, no system
        assert payload["messages"][0]["role"] == "user"


@pytest.mark.asyncio
async def test_generate(client):
    """Test generate method."""
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "Generated text"}

    with patch.object(client.client, "post", return_value=mock_response) as mock_post:
        result = await client.generate("llama2", "Hello")

        assert result["response"] == "Generated text"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/generate"
        assert call_args[1]["json"]["prompt"] == "Hello"


@pytest.mark.asyncio
async def test_health_check_success(client):
    """Test health check returns True when Ollama is available."""
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200

    with patch.object(client.client, "get", return_value=mock_response):
        result = await client.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_health_check_failure(client):
    """Test health check returns False when Ollama is unavailable."""
    with patch.object(client.client, "get", side_effect=Exception("Connection failed")):
        result = await client.health_check()
        assert result is False


@pytest.mark.asyncio
async def test_timeout_error(client):
    """Test timeout error handling."""
    with patch.object(client.client, "post", side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(httpx.TimeoutException):
            await client.chat("llama2", [{"role": "user", "content": "Hi"}])


@pytest.mark.asyncio
async def test_close(client):
    """Test close method."""
    with patch.object(client.client, "aclose", new_callable=AsyncMock) as mock_close:
        await client.close()
        mock_close.assert_called_once()