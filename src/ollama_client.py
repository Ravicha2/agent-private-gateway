"""Ollama client for proxying requests to Ollama."""

import httpx
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class OllamaClient:
    """HTTP client for Ollama API."""

    TOKEN_PRESERVATION_INSTRUCTION = """
[SYSTEM INSTRUCTION] The user input may contain tokens like [TOKEN_EMAIL_1] or
[TOKEN_PHONE_1]. These represent sensitive values that have been tokenized.
Preserve tokens exactly as written in your response. Do not explain, modify,
or expand them. Keep the exact token format in your output.
"""

    def __init__(self, base_url: str, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    def _inject_system_prompt(self, messages: List[Dict]) -> List[Dict]:
        """Add token preservation instruction to system message."""
        if not messages:
            messages = []

        # Check if first message is system
        if messages and messages[0].get("role") == "system":
            content = messages[0].get("content", "")
            messages[0]["content"] = content + self.TOKEN_PRESERVATION_INSTRUCTION
        else:
            # Insert system message at beginning
            messages.insert(0, {
                "role": "system",
                "content": self.TOKEN_PRESERVATION_INSTRUCTION
            })

        return messages

    async def chat(
        self,
        model: str,
        messages: List[Dict],
        inject_prompt: bool = True,
        **kwargs
    ) -> Dict:
        """Send chat request to Ollama."""
        if inject_prompt:
            messages = self._inject_system_prompt(messages)

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            **kwargs
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            logger.error("Ollama request timed out")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            raise

    async def generate(self, model: str, prompt: str, **kwargs) -> Dict:
        """Send generate request to Ollama."""
        payload = {
            "model": model,
            "prompt": prompt,
            **kwargs
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Ollama generate failed: {e}")
            raise

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def health_check(self) -> bool:
        """Check if Ollama is accessible."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except:
            return False