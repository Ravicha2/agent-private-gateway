"""Request and response models for the LLM Gateway."""

from pydantic import BaseModel, Field
from typing import List, Optional


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""

    role: str
    content: str


class ChatRequest(BaseModel):
    """Request model for the /api/chat endpoint."""

    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False


class ChatResponse(BaseModel):
    """Response model for the /api/chat endpoint."""

    model: str
    message: ChatMessage
    done: bool = True