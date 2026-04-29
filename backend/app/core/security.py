"""JWT RS256 token handling and password hashing with argon2id."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt

from app.core.config import settings

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password using argon2id."""
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against an argon2id hash."""
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _read_key(path: str) -> str:
    return Path(path).read_text().strip()


def create_access_token(sub: str) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "type": "access",
    }
    private_key = _read_key(settings.jwt_private_key_path)
    return jwt.encode(payload, private_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(sub: str) -> str:
    """Create a long-lived JWT refresh token."""
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_token_expire_days),
        "type": "refresh",
    }
    private_key = _read_key(settings.jwt_private_key_path)
    return jwt.encode(payload, private_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    public_key = _read_key(settings.jwt_public_key_path)
    return jwt.decode(token, public_key, algorithms=[settings.jwt_algorithm])
