#!/bin/bash
set -e

echo "Starting LLM Gateway..."

# Default values
SENSITIVE_DATA_PATH=${SENSITIVE_DATA_PATH:-/app/sensitive_data.json}
OLLAMA_URL=${OLLAMA_URL:-http://ollama:11434}
LOG_LEVEL=${LOG_LEVEL:-INFO}

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