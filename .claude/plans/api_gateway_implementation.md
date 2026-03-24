# LLM Gateway with Tokenization - Implementation Plan

## Context

**Problem**: Sensitive data (PII, API keys, SSNs, emails, phone numbers) is hardcoded in applications and must never reach LLMs in plaintext. Need a middleware gateway that intercepts requests, tokenizes sensitive values, sends safe input to Ollama, then de-tokenizes responses before returning to users.

**Current Setup**: Ollama running locally, cloud models via Ollama, Docker containerized environment, sensitive data files mounted into containers.

**Goal**: Build a production-ready LLM gateway with secure tokenization/de-tokenization pipeline.

---

## Phase 1: Core Architecture & Data Flow

### Data Flow Diagram

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Application   │────▶│   LLM Gateway    │────▶│     Ollama      │
│   (with PII)    │◄────│   (Middleware)   │◄────│   (Cloud LLM)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
           ┌────────────────┐    ┌─────────────────┐
           │ Sensitive Data │    │ Token Store     │
           │ (Mounted File) │    │ (In-Memory)     │
           └────────────────┘    └─────────────────┘
```

### Request Flow

```
1. INPUT: "Contact Alice at alice@email.com or 555-0123"
              │
              ▼
2. DETECTION: Pattern matcher scans for sensitive values
              │
              ▼
3. TOKENIZATION: Replace with tokens
   "Contact Alice at [TOKEN_EMAIL_1] or [TOKEN_PHONE_1]"
              │
              ▼
4. LLM REQUEST: Send tokenized input to Ollama
              │
              ▼
5. LLM RESPONSE: Model processes tokens, returns response
   "You can reach Alice via [TOKEN_EMAIL_1] or [TOKEN_PHONE_1]"
              │
              ▼
6. DE-TOKENIZATION: Restore original values
   "You can reach Alice via alice@email.com or 555-0123"
              │
              ▼
7. OUTPUT: Return to application
```

### Key Components

| Component | Purpose | File Path (Proposed) |
|-----------|---------|---------------------|
| **FastAPI Gateway** | Main HTTP server, request/response handling | `src/main.py` |
| **SensitiveDataLoader** | Load & parse mounted sensitive data files | `src/loader.py` |
| **PatternMatcher** | Detect sensitive values in text | `src/matcher.py` |
| **Tokenizer** | Replace sensitive values with tokens | `src/tokenizer.py` |
| **Detokenizer** | Restore tokens to original values | `src/detokenizer.py` |
| **OllamaClient** | Proxy requests to Ollama API | `src/ollama_client.py` |
| **TokenStore** | In-memory mapping storage | `src/store.py` |
| **Docker Setup** | Containerization & volume mounts | `Dockerfile`, `docker-compose.yml` |

---

## Phase 2: Detection & Tokenization Strategy

### Detection Method: Hybrid Approach

**Exact String Matching + Regex Patterns**

```python
# Example sensitive_data.json
{
  "emails": ["alice@email.com", "bob@company.org"],
  "phones": ["555-0123", "+1-555-0199"],
  "ssns": ["123-45-6789"],
  "api_keys": ["sk-live-abc123xyz"],
  "custom": ["SuperSecretProject"]
}
```

**Pattern Library** (built-in + user-defined):

```python
PATTERNS = {
    "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    "phone": r'\b(?:\+?1[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}\b',
    "ssn": r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b',
    "api_key": r'sk-[a-zA-Z0-9]{20,}',
}
```

**Matching Priority**:
1. Exact matches from mounted file (highest priority - user explicitly marked as sensitive)
2. Regex pattern matches for known PII types
3. Longest-match-first to prevent partial tokenization

### Token Format

```
Format: [TOKEN_{TYPE}_{ID}]

Examples:
- [TOKEN_EMAIL_1]
- [TOKEN_PHONE_1]
- [TOKEN_SSN_1]
- [TOKEN_CUSTOM_1]

Why this format?
- Brackets make tokens visually distinct and unlikely to be natural output
- TYPE helps debugging and validation
- ID ensures uniqueness per request/session
- LLMs rarely generate text in this exact bracketed format
```

### Consistency Handling

**Same Request Consistency**:
```python
# TokenStore maintains bidirectional mapping per request
store = {
    "value_to_token": {"alice@email.com": "[TOKEN_EMAIL_1]"},
    "token_to_value": {"[TOKEN_EMAIL_1]": "alice@email.com"}
}
```

**Same Value = Same Token**: Hash-based ID generation ensures "alice@email.com" always becomes "[TOKEN_EMAIL_1]" in a single request context.

### Edge Cases

| Case | Handling |
|------|----------|
| Case sensitivity | Store lowercase keys, match case-insensitively |
| Whitespace variations | Normalize whitespace before matching |
| Format variations | Include all known formats in sensitive_data.json |
| Overlapping patterns | Longest match wins (phone in SSN, etc.) |
| Substring matches | Only match complete words (word boundaries) |

---

## Phase 3: Storage & Mapping

### Storage Location: In-Memory Per-Request

**Decision**: In-memory dictionary with request-scoped lifecycle

```python
# FastAPI dependency injection creates isolated store per request
async def get_token_store():
    store = TokenStore()  # New store per request
    try:
        yield store
    finally:
        store.clear()  # Cleanup after response
```

**Why in-memory per-request?**
- Docker containers are ephemeral - persistent storage adds complexity
- Mappings don't need to survive beyond single request-response cycle
- Simpler security model (no data at rest to protect)
- Easier to reason about isolation

### Alternative: Session-Based (if needed later)

If multi-turn conversations require token persistence:
```python
# Use Redis or similar for session-scoped storage
session_store = RedisStore(ttl=3600)  # 1 hour TTL
```

### Security Model

```
┌─────────────────────────────────────────┐
│  Docker Container (Isolated)            │
│  ┌─────────────────────────────────┐  │
│  │  Gateway Process                │  │
│  │  ┌─────────────────────────┐   │  │
│  │  │  TokenStore (memory)    │   │  │
│  │  │  - No persistence         │   │  │
│  │  │  - Cleared per request      │   │  │
│  │  └─────────────────────────┘   │  │
│  └─────────────────────────────────┘  │
│           │                             │
│           ▼                             │
│  ┌─────────────────────────────────┐  │
│  │  Mounted Volume (read-only)     │  │
│  │  /app/sensitive_data.json       │  │
│  └─────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## Phase 4: Ollama Integration

### Request Interception Pattern

**Option A: Transparent Proxy (Recommended)**

```python
# Gateway exposes same endpoints as Ollama
# Application points to gateway instead of Ollama directly

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # 1. Tokenize input
    tokenized_messages = tokenizer.tokenize(request.messages)

    # 2. Forward to Ollama
    ollama_response = await ollama_client.chat(tokenized_messages)

    # 3. De-tokenize response
    response = detokenizer.restore(ollama_response)

    return response
```

**Option B: Library Wrapper** (Alternative)
```python
# Application uses wrapper library
from llm_gateway import OllamaClient
client = OllamaClient()  # Auto-tokenizes
```

**Decision**: Use Option A (Transparent Proxy) - no code changes needed in application, just change the endpoint URL.

### System Prompt Modification

**Add to system prompt automatically**:
```
[SYSTEM INSTRUCTION] The user input may contain tokens like [TOKEN_EMAIL_1] or
[TOKEN_PHONE_1]. These represent sensitive values. Preserve tokens exactly
as written in your response. Do not explain, modify, or expand them.
```

**Implementation**:
```python
def inject_token_preservation_prompt(messages: list):
    if messages and messages[0].get("role") == "system":
        messages[0]["content"] += TOKEN_PRESERVATION_INSTRUCTION
    else:
        messages.insert(0, {"role": "system", "content": TOKEN_PRESERVATION_INSTRUCTION})
    return messages
```

### LLM Behavior Handling

| LLM Output | Handling |
|------------|----------|
| Token verbatim `[TOKEN_EMAIL_1]` | Perfect - direct replacement |
| Modified token `[Token_email_1]` | Fuzzy match + log warning |
| Split token `[TOKEN` + `EMAIL_1]` | Pre-process to normalize |
| Token omitted/paraphrased | Log unmapped tokens, return with placeholders |

---

## Phase 5: De-tokenization & Response Processing

### Token Identification

```python
import re

TOKEN_PATTERN = r'\[TOKEN_[A-Z]+_\d+\]'

def extract_tokens(text: str) -> list[str]:
    return re.findall(TOKEN_PATTERN, text)

def restore_tokens(text: str, store: TokenStore) -> str:
    for token in extract_tokens(text):
        if token in store.token_to_value:
            text = text.replace(token, store.token_to_value[token])
        else:
            logger.warning(f"Unmapped token: {token}")
    return text
```

### Handling LLM Variations

**Fuzzy Matching for Modified Tokens**:
```python
# LLM might output [token_email_1] instead of [TOKEN_EMAIL_1]
def fuzzy_match_token(token: str, store: TokenStore) -> str | None:
    normalized = token.upper().replace(" ", "_")
    return store.token_to_value.get(normalized)
```

### Validation & Failure Modes

```python
class DetokenizationResult:
    text: str
    unmapped_tokens: list[str]
    success: bool

def detokenize(response: str, store: TokenStore) -> DetokenizationResult:
    text = restore_tokens(response, store)
    remaining = extract_tokens(text)

    if remaining:
        return DetokenizationResult(
            text=text,
            unmapped_tokens=remaining,
            success=False
        )
    return DetokenizationResult(text=text, unmapped_tokens=[], success=True)
```

**Failure Strategy**:
1. **Default**: Return response with `[TOKEN_UNMAPPED]` placeholders
2. **Strict mode**: Return 500 error if any tokens remain
3. **Logging**: Always log unmapped tokens for debugging

---

## Phase 6: Implementation Sequencing

### Phase 1: MVP (Week 1)
**Build**: Core tokenization cycle
- FastAPI gateway with single endpoint (`/api/chat`)
- Load sensitive data from JSON file
- Exact string matching only (no regex)
- Tokenize → Ollama → De-tokenize flow
- Single data type (emails)

**Test**: Manual verification with curl

### Phase 2: Robust Detection (Week 2)
**Build**:
- Regex pattern matching for PII
- Multiple data types (email, phone, SSN)
- System prompt injection
- Proper error handling

**Test**: Unit tests for tokenizer/detokenizer

### Phase 3: Docker Integration (Week 2-3)
**Build**:
- Dockerfile with volume mount for sensitive data
- Docker Compose with Ollama service
- Health checks and graceful startup
- Configuration via environment variables

**Test**: End-to-end Docker test

### Phase 4: Security & Monitoring (Week 3)
**Build**:
- Audit logging (no sensitive values in logs)
- Request/response validation
- Token leak detection
- Rate limiting

**Test**: Security audit, load testing

### Phase 5: Production Polish (Week 4)
**Build**:
- Stream response support (for Ollama streaming)
- Metrics and monitoring endpoints
- Documentation
- Configuration validation

---

## Phase 7: Technology Decisions

### Language/Framework: Python + FastAPI

**Rationale**:
- Matches your existing stack (CLAUDE.md preferences)
- FastAPI has excellent async support for proxying
- Easy Docker integration
- Rich ecosystem (Pydantic for validation)

### Key Libraries

| Purpose | Library |
|---------|---------|
| Web framework | `fastapi` |
| HTTP client | `httpx` (async) |
| Data validation | `pydantic` |
| Pattern matching | `re` (built-in) + potentially `presidio` for PII detection |
| Configuration | `pydantic-settings` |
| Logging | `structlog` (structured logging) |

### Docker Structure

```yaml
# docker-compose.yml
version: '3.8'
services:
  llm-gateway:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_URL=http://ollama:11434
      - SENSITIVE_DATA_PATH=/app/sensitive_data.json
    volumes:
      - ./sensitive_data.json:/app/sensitive_data.json:ro
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

---

## Phase 8: Security & Risk Mitigation

### Key Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| **Token leakage in logs** | Never log token-to-value mappings; log only token IDs |
| **Mapping exposure** | In-memory only, cleared after each request |
| **LLM recreates sensitive value** | Use distinctive token format; add system prompt instruction |
| **Sensitive data in error messages** | Sanitize all exceptions before returning |
| **Container compromise** | Read-only mount for sensitive data; non-root user |
| **Request interception** | HTTPS/TLS termination at gateway |

### Audit Logging (Safe Events)

```python
# Log these events WITHOUT sensitive values:
{
    "event": "tokenization_complete",
    "request_id": "uuid",
    "tokens_created": 3,
    "token_types": ["email", "phone"],  # types only, no values
    "duration_ms": 15
}

{
    "event": "detokenization_complete",
    "request_id": "uuid",
    "tokens_restored": 3,
    "unmapped_tokens": 0
}

{
    "event": "sensitive_data_loaded",
    "file_path": "/app/sensitive_data.json",
    "entries_count": 150
}
```

### Data Retention

- **Mappings**: Cleared immediately after each request
- **Logs**: 30 days rotation, no sensitive values
- **Sensitive data file**: Read at startup, cached in memory, never written

---

## Phase 9: Testing Strategy

### Critical Test Cases

| Category | Test Case | Expected Result |
|----------|-----------|-----------------|
| **Basic** | Email in input | Tokenized → LLM → Restored |
| **Multiple instances** | Same email 3 times | Same token used 3 times |
| **Different formats** | "555-0123" vs "(555) 0123" | Both tokenized if both in dictionary |
| **Case sensitivity** | "ALICE@EMAIL.COM" | Matched and tokenized |
| **Substring protection** | "bob@email.com" in "robert@email.com" | Only "bob@email.com" tokenized |
| **Edge case** | Token in original input | Ignored (not a real value) |
| **LLM variation** | LLM outputs lowercase token | Fuzzy matched and restored |
| **Missing token** | LLM drops token entirely | Logged, response returned without it |

### Validation Strategy

```python
# Verify sensitive data never reaches Ollama
def test_tokenization_completeness():
    sensitive_input = "Contact alice@email.com"
    ollama_request = gateway.prepare_request(sensitive_input)
    assert "alice@email.com" not in ollama_request
    assert "[TOKEN_EMAIL_1]" in ollama_request
```

### Safe Testing

- Use fake data in tests: `test@example.com`, `555-0199`
- Never commit real sensitive values
- Mock Ollama responses for unit tests
- Integration tests with local Ollama + fake data

---

## Phase 10: Open Decisions

### Before Implementation Starts

| Decision | Options | Recommendation |
|----------|---------|----------------|
| **Token storage** | In-memory vs Persistent | **In-memory per-request** (simpler, safer) |
| **Scope** | Request vs Session | **Per-request** (stateless, easier to scale) |
| **Pattern matching** | Exact vs Regex vs Hybrid | **Hybrid** (exact for custom, regex for PII) |
| **System prompt** | Modify or not | **Modify** (helps token preservation) |
| **Case sensitivity** | Sensitive or insensitive | **Insensitive matching, normalize storage** |
| **File format** | JSON, YAML, CSV | **JSON** (easy to parse, validates structure) |

### Configuration Schema

```python
# config.py
from pydantic import Field
from pydantic_settings import BaseSettings

class GatewayConfig(BaseSettings):
    ollama_url: str = "http://localhost:11434"
    sensitive_data_path: str = "/app/sensitive_data.json"
    log_level: str = "INFO"
    token_prefix: str = "[TOKEN"
    token_suffix: str = "]"
    enable_regex_patterns: bool = True
    enable_system_prompt_injection: bool = True
    strict_detokenization: bool = False  # Fail on unmapped tokens?
    max_request_size: int = 1024 * 1024  # 1MB
```

---

## Quick Start Checklist

### To Begin Implementation:

1. **Create directory structure**:
   ```
   llm-gateway/
   ├── src/
   │   ├── __init__.py
   │   ├── main.py           # FastAPI app
   │   ├── loader.py         # Sensitive data loader
   │   ├── matcher.py        # Pattern matching
   │   ├── tokenizer.py      # Tokenization logic
   │   ├── detokenizer.py    # De-tokenization logic
   │   ├── store.py          # In-memory token store
   │   └── ollama_client.py  # Ollama API client
   ├── tests/
   ├── Dockerfile
   ├── docker-compose.yml
   ├── requirements.txt
   └── sensitive_data.json   # Mount this
   ```

2. **Start with `main.py`**: Simple FastAPI endpoint that proxies to Ollama

3. **Add tokenization**: Load sensitive data, replace values with tokens

4. **Add de-tokenization**: Restore tokens in Ollama response

5. **Dockerize**: Add Dockerfile with volume mount

6. **Test end-to-end**: Verify sensitive data never reaches Ollama

---

## File References for Implementation

| Component | Proposed File | Reused From |
|-----------|---------------|-------------|
| Gateway server | `src/main.py` | New - FastAPI pattern from CLAUDE.md |
| Config management | `src/config.py` | New - Pydantic Settings pattern |
| Request/Response models | `src/models.py` | New - Pydantic models |
| Token store | `src/store.py` | New - Simple dict wrapper |
| Tokenizer | `src/tokenizer.py` | New - String replacement logic |
| Detokenizer | `src/detokenizer.py` | New - Reverse mapping logic |
| Ollama client | `src/ollama_client.py` | New - httpx async client |
| Sensitive data loader | `src/loader.py` | New - JSON file reader |
| Pattern matcher | `src/matcher.py` | New - Regex + exact matching |

---

## Verification Plan

**Manual Testing**:
```bash
# 1. Start services
docker-compose up

# 2. Send request with sensitive data
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "messages": [{"role": "user", "content": "Email alice@email.com"}]
  }'

# 3. Verify response has original email, not token
# 4. Check Ollama logs - should see token, not email
```

**Automated Testing**:
```bash
pytest tests/ -v
# Test tokenization
# Test detokenization
# Test edge cases
# Test Docker integration
```

---

*This plan provides a complete blueprint for building a secure LLM gateway with tokenization. Start with Phase 1 (MVP) and iterate through each phase.*
