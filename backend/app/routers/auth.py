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
from app.schemas import GitHubLoginURL, GitHubUserRepoItem, TokenResponse, UserResponse
from app.services.auth import create_access_token, decrypt_token, encrypt_token
from app.services.github import fetch_user_repos

router = APIRouter(prefix="/auth", tags=["Auth"])
settings = get_settings()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

# Scopes: read user profile, access email, and (optionally) read repos for webhooks
GITHUB_SCOPES = "read:user user:email repo"

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_SCOPES = "openid email profile"


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


@router.get(
    "/github/repos",
    response_model=list[GitHubUserRepoItem],
    summary="List the authenticated user's GitHub repositories",
)
def list_github_repos(
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """
    Fetches the authenticated user's repositories directly from the GitHub API
    using their stored (encrypted) OAuth token.

    Requires: ``Authorization: Bearer <jwt>``
    """
    if not current_user.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No GitHub token on file — please re-authenticate.",
        )

    try:
        github_token = decrypt_token(current_user.access_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not decrypt GitHub token — please re-authenticate.",
        )

    try:
        raw = fetch_user_repos(github_token, per_page=per_page, page=page)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch GitHub repositories: {exc}",
        )

    return [
        GitHubUserRepoItem(
            id=r["id"],
            name=r["name"],
            full_name=r["full_name"],
            description=r.get("description"),
            private=r.get("private", False),
            html_url=r.get("html_url", ""),
            language=r.get("language"),
            stargazers_count=r.get("stargazers_count", 0),
            forks_count=r.get("forks_count", 0),
            open_issues_count=r.get("open_issues_count", 0),
            default_branch=r.get("default_branch", "main"),
            updated_at=r.get("updated_at"),
            created_at=r.get("created_at"),
            topics=r.get("topics") or [],
            fork=r.get("fork", False),
            archived=r.get("archived", False),
        )
        for r in raw
    ]


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


# ---------------------------------------------------------------------------
# Google OAuth helpers
# ---------------------------------------------------------------------------

def _google_redirect_uri() -> str:
    """Return the callback URL registered with Google OAuth.

    Uses the GOOGLE_REDIRECT_URI setting, which is auto-derived from
    FRONTEND_URL when left blank (see Settings model_validator).
    """
    return settings.GOOGLE_REDIRECT_URI


def _exchange_google_code_for_token(code: str) -> str:
    """POST the OAuth code to Google and return the raw access token string."""
    redirect_uri = _google_redirect_uri()
    with httpx.Client(timeout=15) as client:
        resp = client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token")
    if not token:
        error = data.get("error_description") or data.get("error") or "Unknown error"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth error: {error}",
        )
    return token


def _fetch_google_user(access_token: str) -> dict:
    """Fetch the authenticated user's profile from Google."""
    with httpx.Client(timeout=15) as client:
        resp = client.get(
            GOOGLE_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
    return resp.json()


def _upsert_google_user(google_profile: dict, access_token: str, db: Session) -> User:
    """
    Create or update a User record from Google profile data.
    Uses `sub` (Google's stable user ID) as the lookup key.
    """
    encrypted = encrypt_token(access_token)
    google_id = str(google_profile["sub"])
    email = google_profile.get("email")
    name = google_profile.get("name") or ""
    picture = google_profile.get("picture")

    # Derive a username from the email prefix or name
    username_base = (email.split("@")[0] if email else name.replace(" ", "").lower()) or f"google_{google_id}"

    user = db.query(User).filter(User.google_id == google_id).first()

    if user:
        user.email = email or user.email
        user.avatar_url = picture or user.avatar_url
        user.access_token = encrypted
        user.is_active = True
    else:
        # Ensure username is unique by appending a suffix if needed
        username = username_base
        suffix = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{username_base}{suffix}"
            suffix += 1

        user = User(
            google_id=google_id,
            username=username,
            email=email,
            avatar_url=picture,
            access_token=encrypted,
            is_active=True,
        )
        db.add(user)

    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Google OAuth endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/google/login/redirect",
    summary="Redirect browser directly to Google OAuth",
    include_in_schema=True,
)
def google_login_redirect():
    """Immediately redirects the browser to Google's OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID in .env.",
        )

    redirect_uri = _google_redirect_uri()
    params = urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "prompt": "select_account",
    })
    return RedirectResponse(url=f"{GOOGLE_AUTHORIZE_URL}?{params}")


@router.get(
    "/google/callback",
    summary="Google OAuth callback — exchanges code for JWT",
)
def google_callback(
    code: str = Query(..., description="OAuth code provided by Google"),
    db: Session = Depends(get_db),
):
    """
    Google redirects here after the user authorises the app.

    Steps:
    1. Exchange ``code`` for a Google access token.
    2. Fetch Google user profile.
    3. Upsert user record in the database (token stored encrypted).
    4. Issue a signed JWT.
    5. Redirect the frontend to ``{FRONTEND_URL}/auth/callback?token=<jwt>``.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured on the server.",
        )

    try:
        google_access_token = _exchange_google_code_for_token(code)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to contact Google: {exc}",
        )

    try:
        google_user = _fetch_google_user(google_access_token)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch Google user: {exc}",
        )

    user = _upsert_google_user(google_user, google_access_token, db)
    jwt_token = create_access_token(subject=user.id)

    redirect_url = f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

