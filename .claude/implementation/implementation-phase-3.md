# Phase 3: Tokenization Engine

## Phase Status: ✅ COMPLETED

**Prerequisites**:
- [Phase 1 - Core Architecture](./implementation-phase-1.md) ✅ COMPLETED
- [Phase 2 - Sensitive Data Loading](./implementation-phase-2.md) ✅ COMPLETED

**Next Phase**: [Phase 4 - Ollama Client](./implementation-phase-4.md)

---

## Phase Goal

Implement the tokenization engine that replaces sensitive values with tokens, and the in-memory token store that maintains bidirectional mappings.

---

## Implementation Steps

### Step 3.1: Create Token Store

**Status**: ✅ COMPLETED

**File**: `src/store.py`

**Actions**:
- [ ] Create TokenStore class
- [ ] Add bidirectional mapping dictionaries
- [ ] Implement add method (value → token)
- [ ] Implement get_token and get_value methods
- [ ] Add get_all_tokens method
- [ ] Add clear method for cleanup
- [ ] Handle hash-based token ID generation

**Expected Output**:
```python
# src/store.py
import hashlib
from typing import Dict, Optional, List
from dataclasses import dataclass, field

@dataclass
class TokenStore:
    """In-memory store for token mappings. Created per-request."""
    _value_to_token: Dict[str, str] = field(default_factory=dict)
    _token_to_value: Dict[str, str] = field(default_factory=dict)
    _counters: Dict[str, int] = field(default_factory=dict)

    def _generate_token(self, value: str, token_type: str) -> str:
        """Generate unique token for a value."""
        # Hash for consistency - same value gets same token ID in same request
        value_hash = hashlib.md5(value.lower().encode()).hexdigest()[:8]

        # Increment counter for this type
        self._counters[token_type] = self._counters.get(token_type, 0) + 1
        counter = self._counters[token_type]

        return f"[TOKEN_{token_type.upper()}_{counter}]"

    def add(self, value: str, token_type: str) -> str:
        """Add a value to the store and return its token."""
        # Normalize value for lookup
        normalized = value.lower()

        # Check if already exists
        if normalized in self._value_to_token:
            return self._value_to_token[normalized]

        # Generate new token
        token = self._generate_token(value, token_type)

        # Store bidirectional mapping
        self._value_to_token[normalized] = token
        self._token_to_value[token] = value

        return token

    def get_token(self, value: str) -> Optional[str]:
        """Get token for a value."""
        return self._value_to_token.get(value.lower())

    def get_value(self, token: str) -> Optional[str]:
        """Get original value for a token."""
        return self._token_to_value.get(token)

    def get_all_tokens(self) -> Dict[str, str]:
        """Get all token mappings."""
        return self._token_to_value.copy()

    def has_token(self, token: str) -> bool:
        """Check if token exists."""
        return token in self._token_to_value

    def clear(self) -> None:
        """Clear all mappings."""
        self._value_to_token.clear()
        self._token_to_value.clear()
        self._counters.clear()

    def __len__(self) -> int:
        """Return number of stored mappings."""
        return len(self._value_to_token)
```

---

### Step 3.2: Create Tokenizer

**Status**: ✅ COMPLETED

**File**: `src/tokenizer.py`

**Actions**:
- [ ] Create Tokenizer class
- [ ] Integrate PatternMatcher for finding sensitive values
- [ ] Integrate TokenStore for storing mappings
- [ ] Implement tokenize_text method
- [ ] Implement tokenize_messages method (for ChatMessage list)
- [ ] Handle replacement in reverse order (to preserve positions)
- [ ] Add tokenization result dataclass

**Expected Output**:
```python
# src/tokenizer.py
from typing import List, Dict
from dataclasses import dataclass
from .store import TokenStore
from .matcher import PatternMatcher
from .loader import SensitiveDataLoader

@dataclass
class TokenizationResult:
    text: str
    tokens_created: int
    mappings: Dict[str, str]  # token -> value

class Tokenizer:
    def __init__(self, sensitive_loader: SensitiveDataLoader):
        self.matcher = PatternMatcher(sensitive_loader)

    def tokenize_text(self, text: str, store: TokenStore) -> TokenizationResult:
        """Tokenize a single text string."""
        matches = self.matcher.find_all(text)

        if not matches:
            return TokenizationResult(
                text=text,
                tokens_created=0,
                mappings={}
            )

        # Sort by position (reverse) to replace from end
        matches_sorted = sorted(matches, key=lambda m: m.start, reverse=True)

        result_text = text
        for match in matches_sorted:
            token = store.add(match.value, match.match_type)
            result_text = result_text[:match.start] + token + result_text[match.end:]

        return TokenizationResult(
            text=result_text,
            tokens_created=len(matches),
            mappings=store.get_all_tokens()
        )

    def tokenize_messages(
        self,
        messages: List[Dict],
        store: TokenStore
    ) -> List[Dict]:
        """Tokenize a list of chat messages."""
        tokenized = []
        for msg in messages:
            content = msg.get("content", "")
            result = self.tokenize_text(content, store)

            new_msg = msg.copy()
            new_msg["content"] = result.text
            tokenized.append(new_msg)

        return tokenized
```

---

### Step 3.3: Write Tests for Token Store

**Status**: ✅ COMPLETED

**File**: `tests/test_store.py`

**Actions**:
- [ ] Test adding values generates tokens
- [ ] Test same value returns same token
- [ ] Test get_token and get_value round-trip
- [ ] Test clear method
- [ ] Test token format verification

**Expected Output**:
```python
# tests/test_store.py
import pytest
from src.store import TokenStore

def test_add_creates_token():
    store = TokenStore()
    token = store.add("alice@email.com", "email")
    assert token.startswith("[TOKEN_EMAIL_")
    assert token.endswith("]")

def test_same_value_same_token():
    store = TokenStore()
    token1 = store.add("alice@email.com", "email")
    token2 = store.add("alice@email.com", "email")
    assert token1 == token2

def test_get_value_roundtrip():
    store = TokenStore()
    token = store.add("alice@email.com", "email")
    value = store.get_value(token)
    assert value == "alice@email.com"

def test_case_insensitive():
    store = TokenStore()
    store.add("ALICE@EMAIL.COM", "email")
    token = store.get_token("alice@email.com")
    assert token is not None

def test_clear():
    store = TokenStore()
    store.add("test@example.com", "email")
    store.clear()
    assert len(store) == 0
```

---

### Step 3.4: Write Tests for Tokenizer

**Status**: ✅ COMPLETED

**File**: `tests/test_tokenizer.py`

**Actions**:
- [ ] Test single email tokenization
- [ ] Test multiple values in one text
- [ ] Test messages list tokenization
- [ ] Test no sensitive data (passthrough)
- [ ] Test duplicate values get same token

**Expected Output**:
```python
# tests/test_tokenizer.py
import pytest
from src.tokenizer import Tokenizer
from src.store import TokenStore
from src.loader import SensitiveDataLoader
import tempfile
import json
import os

@pytest.fixture
def tokenizer(tmp_path):
    data = {"emails": ["alice@email.com"], "phones": ["555-0123"]}
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

def test_tokenize_messages(tokenizer):
    store = TokenStore()
    messages = [
        {"role": "user", "content": "Email alice@email.com"},
        {"role": "assistant", "content": "Got it"}
    ]
    result = tokenizer.tokenize_messages(messages, store)
    assert "[TOKEN_EMAIL_1]" in result[0]["content"]
    assert result[1]["content"] == "Got it"  # No change
```

---

### Step 3.5: Integration with FastAPI

**Status**: ✅ COMPLETED

**File**: Modify `src/main.py`

**Actions**:
- [ ] Import Tokenizer and TokenStore
- [ ] Initialize loader in app startup
- [ ] Create TokenStore as FastAPI dependency
- [ ] Add tokenization to /api/chat endpoint
- [ ] Log tokenization results (without values)

**Expected Changes**:
```python
# Add to src/main.py
from .tokenizer import Tokenizer
from .store import TokenStore
from .loader import SensitiveDataLoader
from contextlib import asynccontextmanager

# Global instances
config = GatewayConfig()
sensitive_loader: SensitiveDataLoader = None
tokenizer: Tokenizer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global sensitive_loader, tokenizer
    sensitive_loader = SensitiveDataLoader(config.sensitive_data_path)
    tokenizer = Tokenizer(sensitive_loader)
    yield
    # Cleanup

app = FastAPI(title="LLM Gateway", lifespan=lifespan)

async def get_token_store():
    store = TokenStore()
    try:
        yield store
    finally:
        store.clear()

@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    store: TokenStore = Depends(get_token_store)
):
    # Tokenize messages
    tokenized = tokenizer.tokenize_messages(
        [msg.model_dump() for msg in request.messages],
        store
    )
    # For Phase 3: Return tokenized version (no Ollama yet)
    return {"tokenized": tokenized, "store_size": len(store)}
```

---

## Completion Criteria

This phase is complete when:

- [ ] `src/store.py` manages token mappings
- [ ] `src/tokenizer.py` replaces values with tokens
- [ ] Tests pass: `pytest tests/test_store.py tests/test_tokenizer.py -v`
- [ ] Same value gets same token in a request
- [ ] Token format is `[TOKEN_{TYPE}_{ID}]`
- [ ] /api/chat endpoint returns tokenized messages
- [ ] No sensitive values appear in tokenized output

---

## Files Created/Modified in This Phase

1. `src/store.py` - Token store module
2. `src/tokenizer.py` - Tokenization module
3. `tests/test_store.py` - Store tests
4. `tests/test_tokenizer.py` - Tokenizer tests
5. `src/main.py` - Updated with tokenization

---

## After Completion

1. Update global-implementation.md: Set Phase 3 status to ✅ COMPLETED
2. Move to [Phase 4 - Ollama Client](./implementation-phase-4.md)
