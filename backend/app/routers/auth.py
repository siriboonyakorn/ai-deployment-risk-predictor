"""
GitHub OAuth authentication endpoints.

Flow:
    1. Client calls GET /api/v1/auth/github/login
       → Receives the GitHub OAuth authorization URL (or is redirected).

    2. User approves the OAuth app on GitHub.
       GitHub redirects to: GET /api/v1/auth/github/callback?code=xxx

    3. Backend exchanges the code for an access token, fetches the GitHub
       user profile, upserts the user record (encrypting the token), issues
       a signed JWT, and redirects the frontend with the JWT in the query
       string or returns it directly.

    4. Client stores the JWT and sends it as:
           Authorization: Bearer <jwt>
       on subsequent requests.

Protected routes use Depends(get_current_user) from app.dependencies.
"""

from __future__ import annotations

from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import GitHubLoginURL, TokenResponse, UserResponse
from app.services.auth import create_access_token, encrypt_token

router = APIRouter(prefix="/auth", tags=["Auth"])
settings = get_settings()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

# Scopes: read user profile, access email, and (optionally) read repos for webhooks
GITHUB_SCOPES = "read:user user:email repo"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exchange_code_for_token(code: str) -> str:
    """POST the OAuth code to GitHub and return the raw access token string."""
    with httpx.Client(timeout=15) as client:
        resp = client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
        )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token")
    if not token:
        error = data.get("error_description") or data.get("error") or "Unknown error"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub OAuth error: {error}",
        )
    return token


def _fetch_github_user(access_token: str) -> dict:
    """Fetch the authenticated user's profile from GitHub API."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    with httpx.Client(timeout=15) as client:
        resp = client.get(GITHUB_USER_URL, headers=headers)
        resp.raise_for_status()
        user_data = resp.json()

        # GitHub hides the email on the /user endpoint when it is private.
        # We do a secondary call to /user/emails to get the primary address.
        if not user_data.get("email"):
            emails_resp = client.get(GITHUB_EMAILS_URL, headers=headers)
            if emails_resp.status_code == 200:
                emails = emails_resp.json()
                primary = next(
                    (e["email"] for e in emails if e.get("primary") and e.get("verified")),
                    None,
                )
                user_data["email"] = primary

    return user_data


def _upsert_user(gh: dict, access_token: str, db: Session) -> User:
    """
    Create or update a User record from GitHub profile data.
    The access token is encrypted before being stored.
    """
    encrypted = encrypt_token(access_token)

    user = db.query(User).filter(User.github_id == gh["id"]).first()

    if user:
        # Update mutable fields on every login
        user.username = gh["login"]
        user.email = gh.get("email") or user.email
        user.avatar_url = gh.get("avatar_url")
        user.access_token = encrypted
        user.is_active = True
    else:
        user = User(
            github_id=gh["id"],
            username=gh["login"],
            email=gh.get("email"),
            avatar_url=gh.get("avatar_url"),
            access_token=encrypted,
            is_active=True,
        )
        db.add(user)

    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/github/login",
    response_model=GitHubLoginURL,
    summary="Get GitHub OAuth authorization URL",
)
def github_login():
    """
    Returns the GitHub OAuth authorization URL.

    Clients should redirect the user's browser to the returned ``url``.
    After the user authorises the app, GitHub will redirect back to
    ``/api/v1/auth/github/callback?code=xxx``.

    To initiate a direct browser redirect instead add ``?redirect=true``.
    """
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured. Set GITHUB_CLIENT_ID in .env.",
        )

    params = urlencode({
        "client_id": settings.GITHUB_CLIENT_ID,
        "scope": GITHUB_SCOPES,
        "allow_signup": "true",
    })
    url = f"{GITHUB_AUTHORIZE_URL}?{params}"
    return GitHubLoginURL(url=url)


@router.get(
    "/github/login/redirect",
    summary="Redirect browser directly to GitHub OAuth",
    include_in_schema=True,
)
def github_login_redirect():
    """
    Convenience endpoint that immediately redirects the browser to GitHub.
    Useful when the frontend embeds an ``<a href>`` to this endpoint.
    """
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured.",
        )

    params = urlencode({
        "client_id": settings.GITHUB_CLIENT_ID,
        "scope": GITHUB_SCOPES,
        "allow_signup": "true",
    })
    return RedirectResponse(url=f"{GITHUB_AUTHORIZE_URL}?{params}")


@router.get(
    "/github/callback",
    summary="GitHub OAuth callback — exchanges code for JWT",
)
def github_callback(
    code: str = Query(..., description="OAuth code provided by GitHub"),
    db: Session = Depends(get_db),
):
    """
    GitHub redirects here after the user authorises (or denies) the app.

    Steps:
    1. Exchange ``code`` for a GitHub access token.
    2. Fetch GitHub user profile.
    3. Upsert user record in the database (token stored encrypted).
    4. Issue a signed JWT.
    5. Redirect the frontend to ``{FRONTEND_URL}/auth/callback?token=<jwt>``
       so the client can store it.
    """
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub OAuth is not configured on the server.",
        )

    # 1. Exchange code for GitHub token
    try:
        gh_access_token = _exchange_code_for_token(code)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to contact GitHub: {exc}",
        )

    # 2. Fetch GitHub user
    try:
        gh_user = _fetch_github_user(gh_access_token)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch GitHub user: {exc}",
        )

    # 3. Upsert user (encrypted token stored in DB)
    user = _upsert_user(gh_user, gh_access_token, db)

    # 4. Issue JWT
    jwt_token = create_access_token(subject=user.id)

    # 5. Redirect frontend with token
    redirect_url = f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the currently authenticated user",
)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns the profile of the user identified by the Bearer JWT.

    Requires: ``Authorization: Bearer <jwt>``
    """
    return current_user


@router.post(
    "/logout",
    summary="Invalidate session (client-side logout)",
    status_code=status.HTTP_200_OK,
)
def logout(_: User = Depends(get_current_user)):
    """
    JWTs are stateless — this endpoint simply confirms the token was valid.
    The client should discard the token from local storage on 200 OK.

    For full server-side invalidation, a token-blocklist (Redis) can be
    added in a future iteration.
    """
    return {"message": "Logged out successfully. Please discard your token."}
