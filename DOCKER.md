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

- `OLLAMA_URL`: Ollama API URL (default: http://ollama:11434)
- `SENSITIVE_DATA_PATH`: Path to sensitive data JSON (default: /app/sensitive_data.json)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Troubleshooting

### Ollama not reachable

If you see "Ollama unavailable" errors, ensure:
1. Ollama is running and accessible
2. The OLLAMA_URL environment variable is set correctly
3. Both services are on the same Docker network

### Sensitive data not found

Ensure the `sensitive_data.json` file is mounted at the correct path:
```bash
-v ./sensitive_data.json:/app/sensitive_data.json:ro
```

### Health check fails

Check logs with:
```bash
docker-compose logs llm-gateway
```