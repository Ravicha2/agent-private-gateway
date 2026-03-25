import hashlib
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class TokenStore:
    """In-memory store for token mappings. Created per-request."""
    _value_to_token: Dict[str, str] = field(default_factory=dict)
    _token_to_value: Dict[str, str] = field(default_factory=dict)
    _counters: Dict[str, int] = field(default_factory=dict)

    def _generate_token(self, value: str, token_type: str) -> str:
        """Generate unique token for a value."""
        # Hash for consistency - same value gets same token ID in same request
        value_hash = hashlib.md5(value.lower().encode()).hexdigest()[:8]

        # Increment counter for this type
        self._counters[token_type] = self._counters.get(token_type, 0) + 1
        counter = self._counters[token_type]

        return f"[TOKEN_{token_type.upper()}_{counter}]"

    def add(self, value: str, token_type: str) -> str:
        """Add a value to the store and return its token."""
        # Normalize value for lookup
        normalized = value.lower()

        # Check if already exists
        if normalized in self._value_to_token:
            return self._value_to_token[normalized]

        # Generate new token
        token = self._generate_token(value, token_type)

        # Store bidirectional mapping
        self._value_to_token[normalized] = token
        self._token_to_value[token] = value

        return token

    def get_token(self, value: str) -> Optional[str]:
        """Get token for a value."""
        return self._value_to_token.get(value.lower())

    def get_value(self, token: str) -> Optional[str]:
        """Get original value for a token."""
        return self._token_to_value.get(token)

    def get_all_tokens(self) -> Dict[str, str]:
        """Get all token mappings."""
        return self._token_to_value.copy()

    def has_token(self, token: str) -> bool:
        """Check if token exists."""
        return token in self._token_to_value

    def clear(self) -> None:
        """Clear all mappings."""
        self._value_to_token.clear()
        self._token_to_value.clear()
        self._counters.clear()

    def __len__(self) -> int:
        """Return number of stored mappings."""
        return len(self._value_to_token)