from typing import List, Dict
from dataclasses import dataclass
from .store import TokenStore
from .matcher import PatternMatcher
from .loader import SensitiveDataLoader


@dataclass
class TokenizationResult:
    text: str
    tokens_created: int
    mappings: Dict[str, str]  # token -> value


class Tokenizer:
    def __init__(self, sensitive_loader: SensitiveDataLoader):
        self.matcher = PatternMatcher(sensitive_loader)

    def tokenize_text(self, text: str, store: TokenStore) -> TokenizationResult:
        """Tokenize a single text string."""
        matches = self.matcher.find_all(text)

        if not matches:
            return TokenizationResult(
                text=text,
                tokens_created=0,
                mappings={}
            )

        # Sort by position (reverse) to replace from end
        matches_sorted = sorted(matches, key=lambda m: m.start, reverse=True)

        result_text = text
        for match in matches_sorted:
            token = store.add(match.value, match.match_type)
            result_text = result_text[:match.start] + token + result_text[match.end:]

        return TokenizationResult(
            text=result_text,
            tokens_created=len(store),
            mappings=store.get_all_tokens()
        )

    def tokenize_messages(
        self,
        messages: List[Dict],
        store: TokenStore
    ) -> List[Dict]:
        """Tokenize a list of chat messages."""
        tokenized = []
        for msg in messages:
            content = msg.get("content", "")
            result = self.tokenize_text(content, store)

            new_msg = msg.copy()
            new_msg["content"] = result.text
            tokenized.append(new_msg)

        return tokenized