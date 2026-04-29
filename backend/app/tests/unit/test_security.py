"""Unit tests for core/security.py — password hashing and JWT token handling."""

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify_correct_password(self):
        """Given: a password, When: hash then verify, Then: True."""
        pw = "my-secret-password"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_verify_wrong_password(self):
        """Given: a hashed password, When: verify with wrong password, Then: False."""
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_hash_is_not_plaintext(self):
        """Given: a password, When: hashed, Then: hash differs from original."""
        pw = "plaintext"
        hashed = hash_password(pw)
        assert hashed != pw

    def test_hashes_are_unique(self):
        """Given: same password hashed twice, When: compared, Then: hashes differ (salted)."""
        pw = "same-password"
        h1 = hash_password(pw)
        h2 = hash_password(pw)
        assert h1 != h2


class TestJWTTokens:
    def test_access_token_roundtrip(self):
        """Given: sub, When: create access token then decode, Then: sub matches."""
        sub = "user-123"
        token = create_access_token(sub)
        payload = decode_token(token)
        assert payload["sub"] == sub
        assert payload["type"] == "access"

    def test_refresh_token_roundtrip(self):
        """Given: sub, When: create refresh token then decode, Then: sub matches, type=refresh."""
        sub = "user-456"
        token = create_refresh_token(sub)
        payload = decode_token(token)
        assert payload["sub"] == sub
        assert payload["type"] == "refresh"

    def test_access_and_refresh_tokens_differ(self):
        """Given: same sub, When: create both token types, Then: tokens differ."""
        sub = "user-789"
        access = create_access_token(sub)
        refresh = create_refresh_token(sub)
        assert access != refresh

    def test_token_contains_expiry(self):
        """Given: token created, When: decoded, Then: exp and iat present."""
        token = create_access_token("test")
        payload = decode_token(token)
        assert "exp" in payload
        assert "iat" in payload
        assert payload["exp"] > payload["iat"]
