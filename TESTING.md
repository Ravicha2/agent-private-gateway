# Testing Guide

## Running Tests

### All Tests
```bash
pytest tests/ -v
```

### Unit Tests
```bash
pytest tests/test_complete_unit.py -v
```

### Security Tests
```bash
pytest tests/test_security.py -v
```

### Performance Tests
```bash
pytest tests/test_performance.py -v
```

### Integration Tests
```bash
pytest tests/test_integration.py -v
```

### Specific Test Files
```bash
# Test individual modules
pytest tests/test_loader.py -v
pytest tests/test_matcher.py -v
pytest tests/test_tokenizer.py -v
pytest tests/test_store.py -v
pytest tests/test_detokenizer.py -v
pytest tests/test_ollama_client.py -v
pytest tests/test_main.py -v
```

### With Coverage
```bash
# Install coverage first
pip install pytest-cov

# Run with coverage
pytest tests/ -v --cov=src --cov-report=term-missing
```

## Test Categories

### Unit Tests (`test_complete_unit.py`)
- Test individual components in isolation
- Test config, models, loader edge cases
- Test matcher patterns
- Test tokenizer and store operations
- Test detokenizer and ollama client

### Security Tests (`test_security.py`)
- Verify sensitive values don't leak
- Test token store clearing
- Test case-insensitive handling
- Test special character handling
- Test unmapped token preservation

### Performance Tests (`test_performance.py`)
- Benchmark tokenization speed
- Benchmark detokenization speed
- Test concurrent request handling
- Test store operation speed
- Test pattern matching speed

### Integration Tests (`test_integration.py`)
- Test full request-response cycle
- Test health endpoint
- Test sensitive data tokenization/de-tokenization
- Test multiple messages
- Test invalid request handling

## Test Data

Tests use:
- Fake data (test@example.com, 555-0123, 123-45-6789)
- Temporary files for file-based tests
- Mock Ollama responses
- Never real sensitive data

## Troubleshooting

### Tests fail with import errors
Ensure you're in the project root directory and the package is installed:
```bash
pip install -e .
```

### Tests fail with missing sensitive_data.json
Set the environment variable:
```bash
export GATEWAY_SENSITIVE_DATA_PATH=sensitive_data.json
pytest tests/ -v
```

### Coverage report not generated
Install pytest-cov:
```bash
pip install pytest-cov
```

### Tests timing out
Some integration tests may require Ollama to be running. Run unit tests only:
```bash
pytest tests/test_*.py -v --ignore=tests/test_integration.py
```