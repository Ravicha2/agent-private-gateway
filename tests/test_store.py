import pytest
from src.store import TokenStore


def test_add_creates_token():
    store = TokenStore()
    token = store.add("alice@email.com", "email")
    assert token.startswith("[TOKEN_EMAIL_")
    assert token.endswith("]")


def test_same_value_same_token():
    store = TokenStore()
    token1 = store.add("alice@email.com", "email")
    token2 = store.add("alice@email.com", "email")
    assert token1 == token2


def test_get_value_roundtrip():
    store = TokenStore()
    token = store.add("alice@email.com", "email")
    value = store.get_value(token)
    assert value == "alice@email.com"


def test_case_insensitive():
    store = TokenStore()
    store.add("ALICE@EMAIL.COM", "email")
    token = store.get_token("alice@email.com")
    assert token is not None


def test_clear():
    store = TokenStore()
    store.add("test@example.com", "email")
    store.clear()
    assert len(store) == 0


def test_get_all_tokens():
    store = TokenStore()
    store.add("alice@email.com", "email")
    store.add("555-0123", "phone")
    tokens = store.get_all_tokens()
    assert len(tokens) == 2


def test_has_token():
    store = TokenStore()
    token = store.add("test@example.com", "email")
    assert store.has_token(token) is True
    assert store.has_token("[TOKEN_FAKE_1]") is False


def test_different_types():
    store = TokenStore()
    token_email = store.add("alice@email.com", "email")
    token_phone = store.add("555-0123", "phone")
    assert token_email != token_phone
    assert "EMAIL" in token_email
    assert "PHONE" in token_phone