# Phase 1: Core Architecture & FastAPI Setup

## Phase Status: 🔲 NOT STARTED

**Prerequisites**: None (this is the first phase)

**Next Phase**: [Phase 2 - Sensitive Data Loading](./implementation-phase-2.md)

---

## Phase Goal

Set up the foundational FastAPI application structure with configuration management, request/response models, and a basic endpoint that echoes requests. This establishes the framework for subsequent phases.

---

## Implementation Steps

### Step 1.1: Create Project Directory Structure

**Status**: 🔲 NOT STARTED

**Actions**:
- [ ] Create `src/` directory
- [ ] Create `tests/` directory
- [ ] Create `src/__init__.py`
- [ ] Create `tests/__init__.py`

**Verification**:
```bash
ls -la src/ tests/
# Should show __init__.py files in both directories
```

---

### Step 1.2: Create Configuration Module

**Status**: 🔲 NOT STARTED

**File**: `src/config.py`

**Actions**:
- [ ] Create pydantic-settings based config class
- [ ] Add Ollama URL setting (default: http://localhost:11434)
- [ ] Add sensitive data path setting
- [ ] Add logging level setting
- [ ] Add max request size setting

**Expected Output**:
```python
# src/config.py
from pydantic_settings import BaseSettings

class GatewayConfig(BaseSettings):
    ollama_url: str = "http://localhost:11434"
    sensitive_data_path: str = "/app/sensitive_data.json"
    log_level: str = "INFO"
    max_request_size: int = 1024 * 1024  # 1MB
    # ... other configs
```

---

### Step 1.3: Create Request/Response Models

**Status**: 🔲 NOT STARTED

**File**: `src/models.py`

**Actions**:
- [ ] Create ChatMessage Pydantic model with role and content
- [ ] Create ChatRequest model with model name and messages list
- [ ] Create ChatResponse model
- [ ] Add field validators for content length

**Expected Output**:
```python
# src/models.py
from pydantic import BaseModel, Field
from typing import List

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
```

---

### Step 1.4: Create Main FastAPI Application

**Status**: 🔲 NOT STARTED

**File**: `src/main.py`

**Actions**:
- [ ] Import FastAPI and create app instance
- [ ] Import config and models
- [ ] Create POST /api/chat endpoint (echo version)
- [ ] Add basic health check endpoint GET /health
- [ ] Add request logging middleware
- [ ] Handle basic error responses

**Expected Output**:
```python
# src/main.py
from fastapi import FastAPI
from .config import GatewayConfig
from .models import ChatRequest, ChatResponse

app = FastAPI(title="LLM Gateway")
config = GatewayConfig()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # For Phase 1: Just echo back the request
    return {"model": request.model, "messages": request.messages}
```

---

### Step 1.5: Create Requirements File

**Status**: 🔲 NOT STARTED

**File**: `requirements.txt`

**Actions**:
- [ ] Add fastapi
- [ ] Add uvicorn
- [ ] Add pydantic
- [ ] Add pydantic-settings
- [ ] Add httpx (for future Ollama client)
- [ ] Add structlog (for structured logging)

**Expected Output**:
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
httpx>=0.25.0
structlog>=23.0.0
```

---

### Step 1.6: Create Basic Test

**Status**: 🔲 NOT STARTED

**File**: `tests/test_main.py`

**Actions**:
- [ ] Import TestClient from fastapi.testclient
- [ ] Import app from src.main
- [ ] Write test for /health endpoint
- [ ] Write test for /api/chat endpoint
- [ ] Run tests and verify they pass

**Expected Output**:
```python
# tests/test_main.py
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_chat():
    response = client.post("/api/chat", json={
        "model": "test-model",
        "messages": [{"role": "user", "content": "Hello"}]
    })
    assert response.status_code == 200
```

---

### Step 1.7: Manual Verification

**Status**: 🔲 NOT STARTED

**Actions**:
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Start the server: `uvicorn src.main:app --reload --port 8000`
- [ ] Test health endpoint with curl
- [ ] Test chat endpoint with curl
- [ ] Verify server responds correctly

**Test Commands**:
```bash
# Test health
curl http://localhost:8000/health

# Test chat endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "test", "messages": [{"role": "user", "content": "hello"}]}'
```

---

## Completion Criteria

This phase is complete when:

- [ ] All files exist: `src/config.py`, `src/models.py`, `src/main.py`
- [ ] `requirements.txt` has all dependencies
- [ ] Tests exist and pass (`pytest tests/test_main.py -v`)
- [ ] Server starts successfully (`uvicorn src.main:app`)
- [ ] Health endpoint returns `{"status": "ok"}`
- [ ] Chat endpoint echoes request back
- [ ] No import errors or syntax errors

---

## Files Created in This Phase

1. `src/__init__.py`
2. `src/config.py` - Configuration management
3. `src/models.py` - Pydantic models
4. `src/main.py` - FastAPI application
5. `tests/__init__.py`
6. `tests/test_main.py` - Basic tests
7. `requirements.txt` - Dependencies

---

## Notes for Implementer

- This is a foundational phase - keep it simple
- The /api/chat endpoint is just an echo for now (no tokenization yet)
- Focus on correct structure and imports
- Use Python type hints throughout
- Follow FastAPI patterns from CLAUDE.md
- Use black formatting (4-space indent)

---

## After Completion

1. Update global-implementation.md: Set Phase 1 status to ✅ COMPLETED
2. Move to [Phase 2 - Sensitive Data Loading](./implementation-phase-2.md)
