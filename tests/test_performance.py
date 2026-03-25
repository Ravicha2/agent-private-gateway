"""Performance and load tests."""

import pytest
import time
from src.tokenizer import Tokenizer
from src.detokenizer import Detokenizer
from src.store import TokenStore
from src.matcher import PatternMatcher
from concurrent.futures import ThreadPoolExecutor


class TestPerformance:
    """Performance and load tests."""

    def test_tokenization_speed(self):
        """Tokenization should be fast."""
        text = "Email: test@example.com " * 10
        store = TokenStore()
        tokenizer = Tokenizer(None)

        start = time.time()
        for _ in range(100):
            store.clear()
            tokenizer.tokenize_text(text, store)
        duration = time.time() - start

        # Should process 100 requests quickly
        assert duration < 2.0, f"Tokenization too slow: {duration}s"

    def test_detokenization_speed(self):
        """Detokenization should be fast."""
        text = "Email [TOKEN_EMAIL_1] " * 10
        store = TokenStore()
        store.add("test@example.com", "email")
        detokenizer = Detokenizer()

        start = time.time()
        for _ in range(100):
            detokenizer.restore_tokens(text, store)
        duration = time.time() - start

        # Should process 100 requests quickly
        assert duration < 1.0, f"Detokenization too slow: {duration}s"

    def test_concurrent_requests(self):
        """Should handle concurrent requests."""
        def process_request(i):
            store = TokenStore()
            tokenizer = Tokenizer(None)
            text = f"Email test{i}@example.com"
            return tokenizer.tokenize_text(text, store)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_request, i) for i in range(20)]
            results = [f.result() for f in futures]

        assert len(results) == 20
        # All should have completed
        assert all(r.tokens_created >= 0 for r in results)

    def test_store_operations_speed(self):
        """Token store operations should be fast."""
        store = TokenStore()

        start = time.time()
        for i in range(1000):
            store.add(f"test{i}@example.com", "email")
        duration = time.time() - start

        # Should add 1000 tokens quickly
        assert duration < 1.0, f"Store operations too slow: {duration}s"

    def test_pattern_matching_speed(self):
        """Pattern matching should be fast."""
        text = " ".join([f"test{i}@example.com" for i in range(50)])
        matcher = PatternMatcher()

        start = time.time()
        for _ in range(100):
            matcher.find_all(text)
        duration = time.time() - start

        # Should process 100 times
        assert duration < 2.0, f"Pattern matching too slow: {duration}s"

    def test_multiple_token_types(self):
        """Should handle multiple token types efficiently."""
        store = TokenStore()
        tokenizer = Tokenizer(None)
        text = """
            Email: test@example.com
            Phone: 555-1234
            SSN: 123-45-6789
            Email: another@test.com
        """ * 5

        start = time.time()
        result = tokenizer.tokenize_text(text, store)
        duration = time.time() - start

        assert result.tokens_created > 0
        assert duration < 0.5  # Should be fast