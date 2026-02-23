"""
GitHub API helpers used by the repositories router.

All functions use httpx in synchronous mode so they can be called directly
from FastAPI path operations without requiring async endpoints.
"""

from __future__ import annotations

import re
from typing import Optional

import httpx

GITHUB_API = "https://api.github.com"

# Matches both https://github.com/owner/repo and github.com/owner/repo
_GITHUB_URL_RE = re.compile(
    r"^(?:https?://)?github\.com/([^/]+)/([^/?\s#]+?)(?:\.git)?$"
)


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

def parse_github_url(url: str) -> tuple[str, str]:
    """
    Extract (owner, repo) from a GitHub repository URL.

    Accepts:
        https://github.com/owner/repo
        https://github.com/owner/repo.git
        github.com/owner/repo
    """
    match = _GITHUB_URL_RE.match(url.strip().rstrip("/"))
    if not match:
        raise ValueError(
            f"Could not parse GitHub repository URL: '{url}'. "
            "Expected format: https://github.com/owner/repo"
        )
    return match.group(1), match.group(2)


# ---------------------------------------------------------------------------
# Request helpers
# ---------------------------------------------------------------------------

def _default_headers(token: Optional[str] = None) -> dict[str, str]:
    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


# ---------------------------------------------------------------------------
# GitHub API calls
# ---------------------------------------------------------------------------

def fetch_repo_metadata(
    owner: str,
    repo: str,
    token: Optional[str] = None,
) -> dict:
    """
    Fetch repository metadata from the GitHub REST API.

    Returns the raw GitHub API response dict for /repos/{owner}/{repo}.

    Raises:
        httpx.HTTPStatusError: on 4xx/5xx responses (e.g. 404, 403).
    """
    with httpx.Client(timeout=15) as client:
        resp = client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}",
            headers=_default_headers(token),
        )
        resp.raise_for_status()
        return resp.json()


def fetch_commit_history(
    owner: str,
    repo: str,
    token: Optional[str] = None,
    branch: Optional[str] = None,
    per_page: int = 30,
    page: int = 1,
) -> list[dict]:
    """
    Fetch commit history for a repository from the GitHub REST API.

    Returns a list of raw GitHub commit objects from
    GET /repos/{owner}/{repo}/commits.

    Raises:
        httpx.HTTPStatusError: on 4xx/5xx responses.
    """
    params: dict[str, str | int] = {"per_page": per_page, "page": page}
    if branch:
        params["sha"] = branch

    with httpx.Client(timeout=15) as client:
        resp = client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/commits",
            headers=_default_headers(token),
            params=params,
        )
        resp.raise_for_status()
        return resp.json()
