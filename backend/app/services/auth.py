"""
Authentication utilities.

- JWT creation and verification (for API sessions).
- Fernet symmetric encryption for GitHub access tokens stored in the DB.
  The encryption key is deterministically derived from SECRET_KEY so no
  extra env-var is required.
"""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Fernet key derived from SECRET_KEY (SHA-256 → base64-url-safe 32 bytes)
# ---------------------------------------------------------------------------

def _make_fernet() -> Fernet:
    raw_key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    key = base64.urlsafe_b64encode(raw_key)
    return Fernet(key)


_fernet = _make_fernet()


def encrypt_token(plain_token: str) -> str:
    """Encrypt a GitHub access token for storage in the database."""
    return _fernet.encrypt(plain_token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a GitHub access token retrieved from the database."""
    try:
        return _fernet.decrypt(encrypted_token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Could not decrypt access token — invalid or tampered data.") from exc


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(
    subject: int,
    extra_claims: Optional[dict] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT.

    Args:
        subject: The user's database ID.
        extra_claims: Optional dict of additional payload fields.
        expires_delta: Custom expiry. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Encoded JWT string.
    """
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict = {"sub": str(subject), "exp": expire, "iat": datetime.utcnow()}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT.

    Returns:
        The decoded payload dict.

    Raises:
        JWTError: if the token is invalid, expired, or tampered.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def get_user_id_from_token(token: str) -> int:
    """
    Extract the user ID (``sub`` claim) from a verified JWT.

    Raises:
        JWTError: propagated from decode_access_token.
        ValueError: if ``sub`` is missing or non-numeric.
    """
    payload = decode_access_token(token)
    sub = payload.get("sub")
    if sub is None:
        raise ValueError("JWT is missing 'sub' claim.")
    return int(sub)
