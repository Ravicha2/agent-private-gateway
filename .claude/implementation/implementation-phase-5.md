# Phase 5: De-tokenization & Response Processing

## Phase Status: ✅ COMPLETED

**Prerequisites**:
- [Phase 1 - Core Architecture](./implementation-phase-1.md) ✅ COMPLETED
- [Phase 2 - Sensitive Data Loading](./implementation-phase-2.md) ✅ COMPLETED
- [Phase 3 - Tokenization Engine](./implementation-phase-3.md) ✅ COMPLETED
- [Phase 4 - Ollama Client](./implementation-phase-4.md) ✅ COMPLETED

**Next Phase**: [Phase 6 - Docker Integration](./implementation-phase-6.md)

---

## Phase Goal

Implement de-tokenization to restore original values from tokens in Ollama responses, with fuzzy matching for LLM variations and proper error handling.

---

## Implementation Steps

### Step 5.1: Create De-tokenizer

**Status**: ✅ COMPLETED

**File**: `src/detokenizer.py`

**Actions**:
- [ ] Create Detokenizer class
- [ ] Implement extract_tokens method (regex pattern)
- [ ] Implement restore_tokens method
- [ ] Add fuzzy matching for modified tokens
- [ ] Create DetokenizationResult dataclass
- [ ] Handle unmapped tokens gracefully
- [ ] Add logging for restoration events

**Expected Output**:
```python
# src/detokenizer.py
import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from .store import TokenStore

logger = logging.getLogger(__name__)

@dataclass
class DetokenizationResult:
    text: str
    tokens_restored: int
    unmapped_tokens: List[str]
    success: bool

class Detokenizer:
    # Pattern to match token format: [TOKEN_TYPE_ID]
    TOKEN_PATTERN = r'\[TOKEN_[A-Z_]+_\d+\]'

    # Fuzzy patterns for common LLM variations
    VARIATION_PATTERNS = [
        r'\[token_[a-z_]+_\d+\]',  # lowercase
        r'TOKEN_[A-Z_]+_\d+',      # missing brackets
        r'\[ TOKEN_[A-Z_]+_\d+ \]',  # spaces inside
    ]

    def __init__(self, fuzzy_match: bool = True):
        self.fuzzy_match = fuzzy_match
        self.compiled_pattern = re.compile(self.TOKEN_PATTERN, re.IGNORECASE)

    def extract_tokens(self, text: str) -> List[str]:
        """Extract all tokens from text."""
        return self.compiled_pattern.findall(text)

    def _normalize_token(self, token: str) -> str:
        """Normalize token to standard format."""
        # Remove extra spaces
        token = token.replace(" ", "")
        # Ensure uppercase
        token = token.upper()
        # Ensure brackets
        if not token.startswith("["):
            token = "[" + token
        if not token.endswith("]"):
            token = token + "]"
        return token

    def _fuzzy_match_token(self, token: str, store: TokenStore) -> Optional[str]:
        """Try to match token using fuzzy matching."""
        normalized = self._normalize_token(token)

        # Direct lookup first
        if store.has_token(token):
            return token

        # Try normalized form
        if store.has_token(normalized):
            return normalized

        # Try case-insensitive lookup
        token_upper = token.upper()
        if store.has_token(token_upper):
            return token_upper

        return None

    def restore_tokens(self, text: str, store: TokenStore) -> DetokenizationResult:
        """Restore original values from tokens in text."""
        if not store or len(store) == 0:
            return DetokenizationResult(
                text=text,
                tokens_restored=0,
                unmapped_tokens=[],
                success=True
            )

        tokens = self.extract_tokens(text)
        unmapped = []
        restored_count = 0

        result_text = text

        for token in tokens:
            matched_token = token

            if self.fuzzy_match:
                matched_token = self._fuzzy_match_token(token, store)

            if matched_token and store.has_token(matched_token):
                original_value = store.get_value(matched_token)
                result_text = result_text.replace(token, original_value)
                restored_count += 1
                logger.debug(f"Restored token {token} to value")
            else:
                unmapped.append(token)
                logger.warning(f"Unmapped token found: {token}")

        success = len(unmapped) == 0

        return DetokenizationResult(
            text=result_text,
            tokens_restored=restored_count,
            unmapped_tokens=unmapped,
            success=success
        )

    def restore_chat_response(
        self,
        response: Dict,
        store: TokenStore
    ) -> Dict:
        """Restore tokens in Ollama chat response."""
        if "message" not in response:
            return response

        content = response["message"].get("content", "")
        result = self.restore_tokens(content, store)

        # Return modified response
        restored_response = response.copy()
        restored_response["message"] = response["message"].copy()
        restored_response["message"]["content"] = result.text

        # Add metadata
        restored_response["_detokenization"] = {
            "tokens_restored": result.tokens_restored,
            "unmapped_tokens": result.unmapped_tokens,
            "success": result.success
        }

        return restored_response
```

---

### Step 5.2: Write Tests for De-tokenizer

**Status**: ✅ COMPLETED

**File**: `tests/test_detokenizer.py`

**Actions**:
- [ ] Test exact token restoration
- [ ] Test fuzzy matching for lowercase tokens
- [ ] Test unmapped token handling
- [ ] Test chat response restoration
- [ ] Test multiple tokens in text

**Expected Output**:
```python
# tests/test_detokenizer.py
import pytest
from src.detokenizer import Detokenizer
from src.store import TokenStore

def test_restore_exact_token():
    store = TokenStore()
    store.add("alice@email.com", "email")

    detokenizer = Detokenizer()
    result = detokenizer.restore_tokens("Contact [TOKEN_EMAIL_1] please", store)

    assert result.text == "Contact alice@email.com please"
    assert result.tokens_restored == 1
    assert result.success is True

def test_fuzzy_match_lowercase():
    store = TokenStore()
    store.add("alice@email.com", "email")

    detokenizer = Detokenizer(fuzzy_match=True)
    result = detokenizer.restore_tokens("Contact [token_email_1] please", store)

    assert result.text == "Contact alice@email.com please"
    assert result.tokens_restored == 1

def test_unmapped_token():
    store = TokenStore()
    # Don't add any tokens

    detokenizer = Detokenizer()
    result = detokenizer.restore_tokens("Contact [TOKEN_EMAIL_1] please", store)

    assert result.text == "Contact [TOKEN_EMAIL_1] please"  # Unchanged
    assert result.tokens_restored == 0
    assert "TOKEN_EMAIL_1" in result.unmapped_tokens
    assert result.success is False

def test_restore_chat_response():
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

def test_multiple_tokens():
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
```

---

### Step 5.3: Update Main Application

**Status**: ✅ COMPLETED

**File**: Modify `src/main.py`

**Actions**:
- [ ] Import Detokenizer
- [ ] Initialize detokenizer in lifespan
- [ ] Update /api/chat to de-tokenize Ollama response
- [ ] Handle unmapped tokens (log warning, optional strict mode)
- [ ] Add response metadata

**Expected Changes**:
```python
# Add to src/main.py
from .detokenizer import Detokenizer

# Global instances
detokenizer: Detokenizer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global sensitive_loader, tokenizer, ollama_client, detokenizer
    sensitive_loader = SensitiveDataLoader(config.sensitive_data_path)
    tokenizer = Tokenizer(sensitive_loader)
    ollama_client = OllamaClient(config.ollama_url)
    detokenizer = Detokenizer(fuzzy_match=True)
    yield
    await ollama_client.close()

@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    store: TokenStore = Depends(get_token_store)
):
    try:
        # 1. Tokenize input
        tokenized = tokenizer.tokenize_messages(
            [msg.model_dump() for msg in request.messages],
            store
        )

        # 2. Forward to Ollama
        ollama_response = await ollama_client.chat(
            model=request.model,
            messages=tokenized
        )

        # 3. De-tokenize response
        restored_response = detokenizer.restore_chat_response(
            ollama_response,
            store
        )

        return restored_response

    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

### Step 5.4: End-to-End Test

**Status**: ✅ COMPLETED

**Actions**:
- [ ] Create integration test for full flow
- [ ] Mock Ollama to return token-containing response
- [ ] Verify sensitive values are restored
- [ ] Test complete request-response cycle

**Expected Output**:
```python
# tests/test_end_to_end.py
import pytest
from fastapi.testclient import TestClient
from src.main import app
import json
import tempfile
import os

@pytest.fixture
def client_with_data(tmp_path):
    # Create temp sensitive data
    data = {"emails": ["test@example.com"]}
    data_file = tmp_path / "sensitive.json"
    data_file.write_text(json.dumps(data))

    # Mock the config
    import src.main as main_module
    original_path = main_module.config.sensitive_data_path
    main_module.config.sensitive_data_path = str(data_file)

    yield TestClient(app)

    main_module.config.sensitive_data_path = original_path

def test_full_tokenization_flow(client_with_data, respx_mock):
    # Mock Ollama to return token
    respx_mock.post("http://localhost:11434/api/chat").mock(
        return_value=httpx.Response(200, json={
            "message": {"content": "Email is [TOKEN_EMAIL_1]", "role": "assistant"},
            "done": True
        })
    )

    response = client_with_data.post("/api/chat", json={
        "model": "test",
        "messages": [{"role": "user", "content": "test@example.com"}]
    })

    assert response.status_code == 200
    result = response.json()
    # Should restore original email
    assert "test@example.com" in result["message"]["content"]
    assert "[TOKEN_EMAIL_1]" not in result["message"]["content"]
```

---

### Step 5.5: Manual Verification

**Status**: ✅ COMPLETED

**Actions**:
- [ ] Start Ollama and gateway
- [ ] Send request with sensitive data
- [ ] Verify response contains original values, not tokens
- [ ] Check Ollama logs show only tokens
- [ ] Test with multiple data types

**Test Commands**:
```bash
# Send request with PII
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "messages": [{"role": "user", "content": "Contact alice@email.com"}]
  }'

# Response should show: "You can reach alice@email.com..."
# Ollama should receive: "Contact [TOKEN_EMAIL_1]"
```

---

## Completion Criteria

This phase is complete when:

- [ ] `src/detokenizer.py` restores tokens to values
- [ ] Tests pass: `pytest tests/test_detokenizer.py -v`
- [ ] Full end-to-end test passes
- [ ] /api/chat returns de-tokenized responses
- [ ] Unmapped tokens are logged but don't crash
- [ ] Fuzzy matching handles LLM variations
- [ ] Response includes _detokenization metadata

---

## Files Created/Modified in This Phase

1. `src/detokenizer.py` - De-tokenization module
2. `tests/test_detokenizer.py` - De-tokenizer tests
3. `tests/test_end_to_end.py` - Integration test
4. `src/main.py` - Updated with full pipeline

---

## After Completion

1. Update global-implementation.md: Set Phase 5 status to ✅ COMPLETED
2. Move to [Phase 6 - Docker Integration](./implementation-phase-6.md)
