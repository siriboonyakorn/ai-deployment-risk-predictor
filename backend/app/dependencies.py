"""
FastAPI dependency functions.

Usage in a router:

    from app.dependencies import get_current_user

    @router.get("/me")
    def me(user: User = Depends(get_current_user)):
        ...
"""

from __future__ import annotations

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth import verify_clerk_token

logger = logging.getLogger(__name__)

# The token URL is informational only — clients send: Authorization: Bearer <jwt>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/github/login", auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated. Please sign in via Clerk.",
    headers={"WWW-Authenticate": "Bearer"},
)


def _provision_user(clerk_user_id: str, payload: dict, db: Session) -> User:
    """
    First-time sign-in: create a User row from the Clerk JWT claims.
    Subsequent calls return the existing row without touching the DB.
    """
    email: str | None = payload.get("email")
    name: str = payload.get("name") or payload.get("username") or ""

    # Derive a username from email prefix → name → Clerk user ID
    username_base = (
        email.split("@")[0]
        if email
        else name.replace(" ", "").lower() or clerk_user_id
    )
    # Ensure uniqueness
    username = username_base
    suffix = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{username_base}{suffix}"
        suffix += 1

    user = User(
        clerk_user_id=clerk_user_id,
        username=username,
        email=email,
        avatar_url=payload.get("image_url"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve a Clerk JWT bearer token to a User ORM object.

    On the first request for a new Clerk user the row is auto-created
    (provisioned) from the JWT claims — no separate registration step needed.

    Raises HTTP 401 if the token is absent, invalid, or expired.
    """
    if token is None:
        raise _UNAUTHORIZED

    try:
        payload = verify_clerk_token(token)
        clerk_user_id: str | None = payload.get("sub")
        if not clerk_user_id:
            raise ValueError("JWT missing 'sub' claim")
    except (JWTError, ValueError, Exception) as exc:
        logger.warning("Clerk JWT verification failed: %s", exc)
        raise _UNAUTHORIZED

    try:
        user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
        if user is None:
            user = _provision_user(clerk_user_id, payload, db)
    except Exception as exc:
        logger.error("User provisioning failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"User provisioning error: {exc}")

    if not user.is_active:
        raise _UNAUTHORIZED

    return user


def get_optional_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Like get_current_user but returns None instead of raising 401."""
    if token is None:
        return None
    try:
        payload = verify_clerk_token(token)
        clerk_user_id = payload.get("sub")
        if not clerk_user_id:
            return None
        user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
        if user is None:
            user = _provision_user(clerk_user_id, payload, db)
        return user if user.is_active else None
    except Exception:
        return None
