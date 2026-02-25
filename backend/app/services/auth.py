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


# ---------------------------------------------------------------------------
# Clerk JWT verification
# ---------------------------------------------------------------------------

_clerk_jwks_cache: dict | None = None
_clerk_jwks_issuer: str | None = None


def _fetch_clerk_jwks(issuer: str) -> dict:
    """Fetch (and cache) the JWKS for a given Clerk issuer URL."""
    global _clerk_jwks_cache, _clerk_jwks_issuer
    if _clerk_jwks_cache is not None and _clerk_jwks_issuer == issuer:
        return _clerk_jwks_cache

    import httpx
    jwks_url = f"{issuer.rstrip('/')}/.well-known/jwks.json"
    response = httpx.get(jwks_url, timeout=10)
    response.raise_for_status()
    _clerk_jwks_cache = response.json()
    _clerk_jwks_issuer = issuer
    return _clerk_jwks_cache


def verify_clerk_token(token: str) -> dict:
    """
    Verify a Clerk-issued JWT and return its claims.

    Steps:
    1. Decode without verification to extract the ``iss`` (issuer) claim.
    2. Fetch the issuer's JWKS public keys (cached in memory).
    3. Verify the JWT signature, expiry, and issuer.

    Raises:
        JWTError: if the token is invalid, expired, tampered, or the JWKS
                  cannot be fetched.
        ValueError: if required claims are missing.
    """
    unverified_claims = jwt.get_unverified_claims(token)
    issuer = unverified_claims.get("iss", "")
    if not issuer:
        raise ValueError("Clerk JWT is missing the 'iss' claim.")

    jwks = _fetch_clerk_jwks(issuer)

    # Clerk tokens use RS256; audience is not always set so we skip that check
    payload = jwt.decode(
        token,
        jwks,
        algorithms=["RS256"],
        issuer=issuer,
        options={"verify_aud": False},
    )
    return payload
