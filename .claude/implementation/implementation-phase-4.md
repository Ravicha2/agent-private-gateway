# Phase 4: Ollama Client & Proxy Integration

## Phase Status: 🔲 NOT STARTED

**Prerequisites**:
- [Phase 1 - Core Architecture](./implementation-phase-1.md) ✅ COMPLETED
- [Phase 2 - Sensitive Data Loading](./implementation-phase-2.md) ✅ COMPLETED
- [Phase 3 - Tokenization Engine](./implementation-phase-3.md) ✅ COMPLETED

**Next Phase**: [Phase 5 - De-tokenization](./implementation-phase-5.md)

---

## Phase Goal

Implement the Ollama client that proxies tokenized requests to Ollama and receives responses. Add system prompt injection for token preservation.

---

## Implementation Steps

### Step 4.1: Create Ollama Client

**Status**: 🔲 NOT STARTED

**File**: `src/ollama_client.py`

**Actions**:
- [ ] Create OllamaClient class using httpx.AsyncClient
- [ ] Implement chat method for /api/chat endpoint
- [ ] Implement generate method for /api/generate
- [ ] Add timeout and error handling
- [ ] Add retry logic for failed requests
- [ ] Support streaming responses (for Phase 7)

**Expected Output**:
```python
# src/ollama_client.py
import httpx
from typing import List, Dict, AsyncGenerator, Optional
import json
import logging

logger = logging.getLogger(__name__)

class OllamaClient:
    TOKEN_PRESERVATION_INSTRUCTION = """
[SYSTEM INSTRUCTION] The user input may contain tokens like [TOKEN_EMAIL_1] or
[TOKEN_PHONE_1]. These represent sensitive values that have been tokenized.
Preserve tokens exactly as written in your response. Do not explain, modify,
or expand them. Keep the exact token format in your output.
"""

    def __init__(self, base_url: str, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    def _inject_system_prompt(self, messages: List[Dict]) -> List[Dict]:
        """Add token preservation instruction to system message."""
        if not messages:
            messages = []

        # Check if first message is system
        if messages and messages[0].get("role") == "system":
            content = messages[0].get("content", "")
            messages[0]["content"] = content + self.TOKEN_PRESERVATION_INSTRUCTION
        else:
            # Insert system message at beginning
            messages.insert(0, {
                "role": "system",
                "content": self.TOKEN_PRESERVATION_INSTRUCTION
            })

        return messages

    async def chat(
        self,
        model: str,
        messages: List[Dict],
        inject_prompt: bool = True,
        **kwargs
    ) -> Dict:
        """Send chat request to Ollama."""
        if inject_prompt:
            messages = self._inject_system_prompt(messages)

        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            logger.error("Ollama request timed out")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            raise

    async def generate(self, model: str, prompt: str, **kwargs) -> Dict:
        """Send generate request to Ollama."""
        payload = {
            "model": model,
            "prompt": prompt,
            **kwargs
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Ollama generate failed: {e}")
            raise

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def health_check(self) -> bool:
        """Check if Ollama is accessible."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except:
            return False
```

---

### Step 4.2: Create Tests for Ollama Client

**Status**: 🔲 NOT STARTED

**File**: `tests/test_ollama_client.py`

**Actions**:
- [ ] Mock Ollama responses with pytest-httpx
- [ ] Test chat method sends correct payload
- [ ] Test system prompt injection
- [ ] Test error handling
- [ ] Test health check

**Expected Output**:
```python
# tests/test_ollama_client.py
import pytest
import httpx
from src.ollama_client import OllamaClient

@pytest.fixture
def client():
    return OllamaClient("http://localhost:11434")

@pytest.mark.asyncio
async def test_chat_sends_request(respx_mock, client):
    route = respx_mock.post("http://localhost:11434/api/chat").mock(
        return_value=httpx.Response(200, json={"message": {"content": "Hello"}})
    )

    result = await client.chat("llama2", [{"role": "user", "content": "Hi"}])

    assert result["message"]["content"] == "Hello"
    assert route.called

@pytest.mark.asyncio
async def test_system_prompt_injection(respx_mock, client):
    captured = {}

    def capture_request(request):
        captured["json"] = request.content
        return httpx.Response(200, json={"message": {"content": "Hello"}})

    respx_mock.post("http://localhost:11434/api/chat").mock(side_effect=capture_request)

    await client.chat("llama2", [{"role": "user", "content": "Hi"}])

    import json
    payload = json.loads(captured["json"])
    assert payload["messages"][0]["role"] == "system"
    assert "TOKEN" in payload["messages"][0]["content"]
```

---

### Step 4.3: Update Main Application

**Status**: 🔲 NOT STARTED

**File**: Modify `src/main.py`

**Actions**:
- [ ] Import OllamaClient
- [ ] Initialize client in lifespan
- [ ] Update /api/chat to forward to Ollama
- [ ] Add error handling for Ollama failures
- [ ] Add /api/tags endpoint for model listing

**Expected Changes**:
```python
# Add to src/main.py
from .ollama_client import OllamaClient

# Global instances
ollama_client: OllamaClient = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global sensitive_loader, tokenizer, ollama_client
    sensitive_loader = SensitiveDataLoader(config.sensitive_data_path)
    tokenizer = Tokenizer(sensitive_loader)
    ollama_client = OllamaClient(config.ollama_url)
    yield
    await ollama_client.close()

@app.get("/api/tags")
async def list_models():
    """Proxy to Ollama model list."""
    try:
        response = await ollama_client.client.get(f"{ollama_client.base_url}/api/tags")
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {e}")

@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    store: TokenStore = Depends(get_token_store)
):
    try:
        # Tokenize input
        tokenized = tokenizer.tokenize_messages(
            [msg.model_dump() for msg in request.messages],
            store
        )

        # Forward to Ollama
        ollama_response = await ollama_client.chat(
            model=request.model,
            messages=tokenized
        )

        # For Phase 4: Return raw Ollama response (de-tokenization in Phase 5)
        return ollama_response

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Ollama request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### Step 4.4: Manual Integration Test

**Status**: 🔲 NOT STARTED

**Actions**:
- [ ] Start Ollama locally (if available)
- [ ] Test health check: `curl http://localhost:8000/health`
- [ ] Test model listing: `curl http://localhost:8000/api/tags`
- [ ] Test chat with tokenized input
- [ ] Verify Ollama receives tokenized messages

**Test Commands**:
```bash
# Start Ollama (separate terminal)
ollama serve

# Start gateway
uvicorn src.main:app --reload

# Test chat (should show Ollama processing tokens)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "llama2", "messages": [{"role": "user", "content": "Hello [TOKEN_EMAIL_1]"}]}'
```

---

## Completion Criteria

This phase is complete when:

- [ ] `src/ollama_client.py` proxies requests to Ollama
- [ ] System prompt injection includes token preservation instructions
- [ ] Tests pass: `pytest tests/test_ollama_client.py -v`
- [ ] /api/chat forwards to Ollama
- [ ] /api/tags lists available models
- [ ] Error handling returns proper HTTP status codes
- [ ] Timeout handling works

---

## Files Created/Modified in This Phase

1. `src/ollama_client.py` - Ollama HTTP client
2. `tests/test_ollama_client.py` - Client tests
3. `src/main.py` - Updated with Ollama integration

---

## After Completion

1. Update global-implementation.md: Set Phase 4 status to ✅ COMPLETED
2. Move to [Phase 5 - De-tokenization](./implementation-phase-5.md)
