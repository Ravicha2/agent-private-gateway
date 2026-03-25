# Phase 6: Docker Integration

## Phase Status: ✅ COMPLETED

**Prerequisites**:
- [Phase 1 - Core Architecture](./implementation-phase-1.md) ✅ COMPLETED
- [Phase 2 - Sensitive Data Loading](./implementation-phase-2.md) ✅ COMPLETED
- [Phase 3 - Tokenization Engine](./implementation-phase-3.md) ✅ COMPLETED
- [Phase 4 - Ollama Client](./implementation-phase-4.md) ✅ COMPLETED
- [Phase 5 - De-tokenization](./implementation-phase-5.md) ✅ COMPLETED

**Next Phase**: [Phase 7 - Testing & Validation](./implementation-phase-7.md)

---

## Phase Goal

Containerize the gateway with Docker and Docker Compose, including volume mounts for sensitive data and integration with Ollama service.

---

## Implementation Steps

### Step 6.1: Create Dockerfile

**Status**: ✅ COMPLETED

**File**: `Dockerfile`

**Actions**:
- [ ] Use Python 3.11-slim base image
- [ ] Set working directory to /app
- [ ] Copy requirements.txt and install dependencies
- [ ] Copy source code
- [ ] Create non-root user for security
- [ ] Expose port 8000
- [ ] Set entrypoint to uvicorn

**Expected Output**:
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Step 6.2: Create Docker Compose Configuration

**Status**: ✅ COMPLETED

**File**: `docker-compose.yml`

**Actions**:
- [ ] Define llm-gateway service
- [ ] Define ollama service
- [ ] Configure volume mount for sensitive_data.json
- [ ] Set environment variables
- [ ] Add health checks
- [ ] Configure service dependencies

**Expected Output**:
```yaml
# docker-compose.yml
version: '3.8'

services:
  llm-gateway:
    build: .
    container_name: llm-gateway
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_URL=http://ollama:11434
      - SENSITIVE_DATA_PATH=/app/sensitive_data.json
      - LOG_LEVEL=INFO
    volumes:
      - ./sensitive_data.json:/app/sensitive_data.json:ro
    depends_on:
      ollama:
        condition: service_started
    networks:
      - gateway-network
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s

  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - gateway-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

volumes:
  ollama_data:
    driver: local

networks:
  gateway-network:
    driver: bridge
```

---

### Step 6.3: Create Docker Entrypoint Script

**Status**: ✅ COMPLETED

**File**: `entrypoint.sh`

**Actions**:
- [ ] Create shell script for container startup
- [ ] Validate sensitive data file exists
- [ ] Wait for Ollama to be ready (optional)
- [ ] Start uvicorn server

**Expected Output**:
```bash
#!/bin/bash
# entrypoint.sh
set -e

echo "Starting LLM Gateway..."

# Check sensitive data file
if [ ! -f "$SENSITIVE_DATA_PATH" ]; then
    echo "Warning: Sensitive data file not found at $SENSITIVE_DATA_PATH"
    echo "Creating empty file..."
    echo '{}' > "$SENSITIVE_DATA_PATH"
fi

echo "Configuration:"
echo "  OLLAMA_URL: $OLLAMA_URL"
echo "  SENSITIVE_DATA_PATH: $SENSITIVE_DATA_PATH"
echo "  LOG_LEVEL: $LOG_LEVEL"

# Execute the main command
exec "$@"
```

**Update Dockerfile**:
```dockerfile
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Step 6.4: Create .dockerignore

**Status**: ✅ COMPLETED

**File**: `.dockerignore`

**Actions**:
- [ ] Ignore Python cache files
- [ ] Ignore git directory
- [ ] Ignore local virtual environments
- [ ] Ignore test cache
- [ ] Keep sensitive_data.json template

**Expected Output**:
```
# .dockerignore
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.git/
.gitignore
.pytest_cache/
.coverage
htmlcov/
.tox/
.venv/

# Don't ignore these
!sensitive_data.json
!requirements.txt
```

---

### Step 6.5: Test Docker Build

**Status**: ✅ COMPLETED

**Actions**:
- [ ] Run `docker build -t llm-gateway .`
- [ ] Verify image builds without errors
- [ ] Check image size is reasonable
- [ ] Verify non-root user is used

**Test Commands**:
```bash
# Build image
docker build -t llm-gateway .

# Verify image
docker images | grep llm-gateway

# Check user
docker run --rm llm-gateway whoami
# Should output: appuser
```

---

### Step 6.6: Test Docker Compose

**Status**: ✅ COMPLETED

**Actions**:
- [ ] Start services: `docker-compose up -d`
- [ ] Check service health: `docker-compose ps`
- [ ] Test gateway health endpoint
- [ ] Test chat endpoint through gateway
- [ ] Stop services: `docker-compose down`

**Test Commands**:
```bash
# Start services
docker-compose up -d

# Wait for startup
sleep 10

# Check health
curl http://localhost:8000/health

# Test chat (if Ollama has models)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "llama2", "messages": [{"role": "user", "content": "Hello"}]}'

# View logs
docker-compose logs -f llm-gateway

# Cleanup
docker-compose down
```

---

### Step 6.7: Create Docker Documentation

**Status**: ✅ COMPLETED

**File**: `DOCKER.md`

**Actions**:
- [ ] Document build command
- [ ] Document run command
- [ ] Document environment variables
- [ ] Document volume mounts
- [ ] Include troubleshooting section

**Expected Output**:
```markdown
# Docker Usage

## Build
```bash
docker build -t llm-gateway .
```

## Run
```bash
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/sensitive_data.json:/app/sensitive_data.json:ro \
  -e OLLAMA_URL=http://host.docker.internal:11434 \
  llm-gateway
```

## Docker Compose
```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Rebuild
docker-compose up --build
```

## Environment Variables
- `OLLAMA_URL`: Ollama API URL
- `SENSITIVE_DATA_PATH`: Path to sensitive data JSON
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
```

---

## Completion Criteria

This phase is complete when:

- [ ] `Dockerfile` builds successfully
- [ ] `docker-compose.yml` starts both services
- [ ] Image uses non-root user
- [ ] Health checks are configured
- [ ] Volume mount for sensitive data works
- [ ] Gateway can communicate with Ollama container
- [ ] `docker-compose up` brings up working system
- [ ] `docker-compose down` cleans up properly

---

## Files Created in This Phase

1. `Dockerfile` - Container definition
2. `docker-compose.yml` - Multi-service orchestration
3. `entrypoint.sh` - Container startup script
4. `.dockerignore` - Build context exclusions
5. `DOCKER.md` - Docker usage documentation

---

## After Completion

1. Update global-implementation.md: Set Phase 6 status to ✅ COMPLETED
2. Move to [Phase 7 - Testing & Validation](./implementation-phase-7.md)
