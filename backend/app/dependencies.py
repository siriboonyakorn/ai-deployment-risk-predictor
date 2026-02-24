"""
FastAPI dependency functions.

Usage in a router:

    from app.dependencies import get_current_user

    @router.get("/me")
    def me(user: User = Depends(get_current_user)):
        ...
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth import get_user_id_from_token

# The token URL is not a login form, but FastAPI needs a value.
# Clients send: Authorization: Bearer <jwt>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/github/login", auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated. Please log in via GitHub OAuth.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve the JWT bearer token to a User ORM object.

    Raises HTTP 401 if the token is absent, invalid, expired, or the user
    no longer exists in the database.
    """
    if token is None:
        raise _UNAUTHORIZED

    try:
        user_id = get_user_id_from_token(token)
    except (JWTError, ValueError):
        raise _UNAUTHORIZED

    user = db.get(User, user_id)
    if user is None or not user.is_active:
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
        user_id = get_user_id_from_token(token)
        user = db.get(User, user_id)
        return user if (user and user.is_active) else None
    except (JWTError, ValueError):
        return None
