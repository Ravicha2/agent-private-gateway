"""Main FastAPI application for the LLM Gateway."""

import structlog
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import AsyncGenerator

from .config import GatewayConfig
from .models import ChatRequest, ChatResponse
from .tokenizer import Tokenizer
from .store import TokenStore
from .loader import SensitiveDataLoader
from .ollama_client import OllamaClient


# Global instances
config = GatewayConfig()
logger = structlog.get_logger()
sensitive_loader: SensitiveDataLoader = None
tokenizer: Tokenizer = None
ollama_client: OllamaClient = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan - initialize and cleanup resources."""
    global sensitive_loader, tokenizer, ollama_client
    sensitive_loader = SensitiveDataLoader(config.sensitive_data_path)
    tokenizer = Tokenizer(sensitive_loader)
    ollama_client = OllamaClient(config.ollama_url)
    logger.info("tokenization_initialized", sensitive_data_path=str(config.sensitive_data_path))
    yield
    # Cleanup
    await ollama_client.close()


def get_token_store() -> TokenStore:
    """Dependency that provides a TokenStore per request."""
    store = TokenStore()
    try:
        yield store
    finally:
        store.clear()


# Create FastAPI app
app = FastAPI(
    title="LLM Gateway",
    description="Secure middleware gateway with tokenization for LLM requests",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info(
        "request_received",
        method=request.method,
        path=request.url.path,
    )
    response = await call_next(request)
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )
    return response


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/tags")
async def list_models():
    """Proxy to Ollama model list."""
    try:
        response = await ollama_client.client.get(f"{ollama_client.base_url}/api/tags")
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama unavailable: {e}")


@app.post("/api/chat")
async def chat(request: ChatRequest, store: TokenStore = Depends(get_token_store)):
    """
    Chat endpoint - handles LLM requests with tokenization and proxies to Ollama.
    """
    try:
        # Tokenize input
        tokenized = tokenizer.tokenize_messages(
            [msg.model_dump() for msg in request.messages],
            store
        )

        logger.info(
            "request_tokenized",
            tokens_created=len(store),
            model=request.model,
        )

        # Forward to Ollama
        ollama_response = await ollama_client.chat(
            model=request.model,
            messages=tokenized
        )

        # Return raw Ollama response (de-tokenization in Phase 5)
        return ollama_response

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Ollama request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(
        "uncaught_exception",
        error=str(exc),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )