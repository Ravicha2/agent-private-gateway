"""De-tokenization module for restoring original values from tokens."""

import re
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from .store import TokenStore

logger = logging.getLogger(__name__)


@dataclass
class DetokenizationResult:
    """Result of de-tokenization operation."""
    text: str
    tokens_restored: int
    unmapped_tokens: List[str]
    success: bool


class Detokenizer:
    """De-tokenizer that restores original values from tokens in text."""

    # Pattern to match token format: [TOKEN_TYPE_ID]
    TOKEN_PATTERN = r'\[TOKEN_[A-Z_]+_\d+\]'

    def __init__(self, fuzzy_match: bool = True):
        self.fuzzy_match = fuzzy_match
        self.compiled_pattern = re.compile(self.TOKEN_PATTERN, re.IGNORECASE)

    def extract_tokens(self, text: str) -> List[str]:
        """Extract all tokens from text."""
        return self.compiled_pattern.findall(text)

    def _normalize_token(self, token: str) -> str:
        """Normalize token to standard format."""
        # Remove extra spaces
        token = token.replace(" ", "")
        # Ensure uppercase
        token = token.upper()
        # Ensure brackets
        if not token.startswith("["):
            token = "[" + token
        if not token.endswith("]"):
            token = token + "]"
        return token

    def _fuzzy_match_token(self, token: str, store: TokenStore) -> Optional[str]:
        """Try to match token using fuzzy matching."""
        normalized = self._normalize_token(token)

        # Direct lookup first
        if store.has_token(token):
            return token

        # Try normalized form
        if store.has_token(normalized):
            return normalized

        # Try case-insensitive lookup
        token_upper = token.upper()
        if store.has_token(token_upper):
            return token_upper

        return None

    def restore_tokens(self, text: str, store: TokenStore) -> DetokenizationResult:
        """Restore original values from tokens in text."""
        tokens = self.extract_tokens(text)
        unmapped = []
        restored_count = 0

        result_text = text

        # Handle empty or None store
        if not store or len(store) == 0:
            return DetokenizationResult(
                text=text,
                tokens_restored=0,
                unmapped_tokens=tokens,
                success=len(tokens) == 0
            )

        for token in tokens:
            matched_token = token

            if self.fuzzy_match:
                matched_token = self._fuzzy_match_token(token, store)

            if matched_token and store.has_token(matched_token):
                original_value = store.get_value(matched_token)
                result_text = result_text.replace(token, original_value)
                restored_count += 1
                logger.debug(f"Restored token {token} to value")
            else:
                unmapped.append(token)
                logger.warning(f"Unmapped token found: {token}")

        success = len(unmapped) == 0

        return DetokenizationResult(
            text=result_text,
            tokens_restored=restored_count,
            unmapped_tokens=unmapped,
            success=success
        )

    def restore_chat_response(
        self,
        response: Dict,
        store: TokenStore
    ) -> Dict:
        """Restore tokens in Ollama chat response."""
        if "message" not in response:
            return response

        content = response["message"].get("content", "")
        result = self.restore_tokens(content, store)

        # Return modified response
        restored_response = response.copy()
        restored_response["message"] = response["message"].copy()
        restored_response["message"]["content"] = result.text

        # Add metadata
        restored_response["_detokenization"] = {
            "tokens_restored": result.tokens_restored,
            "unmapped_tokens": result.unmapped_tokens,
            "success": result.success
        }

        return restored_response