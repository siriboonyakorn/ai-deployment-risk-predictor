"""
GitHub API helpers used by the repositories router.

All functions use httpx in synchronous mode so they can be called directly
from FastAPI path operations without requiring async endpoints.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

from app.exceptions import ExternalServiceError, NotFoundError, ForbiddenError, ValidationError

logger = logging.getLogger(__name__)

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

    Raises:
        ValidationError: when the URL format is unrecognised.
    """
    match = _GITHUB_URL_RE.match(url.strip().rstrip("/"))
    if not match:
        raise ValidationError(
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


def _handle_github_error(exc: httpx.HTTPStatusError, context: str = "GitHub API") -> None:
    """Translate common GitHub HTTP errors into app exceptions."""
    code = exc.response.status_code
    if code == 404:
        raise NotFoundError(context)
    if code == 403:
        raise ForbiddenError("GitHub API rate limit exceeded or token lacks permissions.")
    raise ExternalServiceError("GitHub", f"HTTP {code}")


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
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    logger.info("Fetching repo metadata: %s/%s", owner, repo)
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, headers=_default_headers(token))
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        _handle_github_error(exc, f"Repository '{owner}/{repo}'")
    except httpx.RequestError as exc:
        raise ExternalServiceError("GitHub", str(exc))


def fetch_user_repos(
    token: str,
    per_page: int = 100,
    page: int = 1,
    sort: str = "updated",
    affiliation: str = "owner,collaborator,organization_member",
) -> list[dict]:
    """Fetch the authenticated user's GitHub repositories."""
    params: dict[str, str | int] = {
        "per_page": per_page,
        "page": page,
        "sort": sort,
        "affiliation": affiliation,
    }
    logger.debug("Fetching user repos page=%s per_page=%s", page, per_page)
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{GITHUB_API}/user/repos",
                headers=_default_headers(token),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        _handle_github_error(exc, "user repos")
    except httpx.RequestError as exc:
        raise ExternalServiceError("GitHub", str(exc))


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
    """
    params: dict[str, str | int] = {"per_page": per_page, "page": page}
    if branch:
        params["sha"] = branch

    logger.debug("Fetching commits %s/%s branch=%s page=%s", owner, repo, branch, page)
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/commits",
                headers=_default_headers(token),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        _handle_github_error(exc, f"commits for '{owner}/{repo}'")
    except httpx.RequestError as exc:
        raise ExternalServiceError("GitHub", str(exc))


def fetch_commit_detail(
    owner: str,
    repo: str,
    sha: str,
    token: Optional[str] = None,
) -> dict:
    """
    Fetch a **single** commit with full stats (lines added / deleted,
    files changed) from GET /repos/{owner}/{repo}/commits/{sha}.

    The list-commits endpoint does *not* include per-commit stats, so this
    call is required to populate the metrics columns in the database.
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/commits/{sha}"
    logger.debug("Fetching commit detail %s/%s @ %s", owner, repo, sha[:7])
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, headers=_default_headers(token))
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        _handle_github_error(exc, f"commit {sha[:7]}")
    except httpx.RequestError as exc:
        raise ExternalServiceError("GitHub", str(exc))


def fetch_commits_paginated(
    owner: str,
    repo: str,
    token: Optional[str] = None,
    branch: Optional[str] = None,
    total: int = 100,
) -> list[dict]:
    """
    Fetch up to *total* commits across multiple pages.

    Returns a flat list of raw GitHub commit objects (newest first).
    """
    per_page = min(total, 100)
    collected: list[dict] = []
    page = 1

    while len(collected) < total:
        batch = fetch_commit_history(
            owner, repo, token=token, branch=branch,
            per_page=per_page, page=page,
        )
        if not batch:
            break
        collected.extend(batch)
        if len(batch) < per_page:
            break  # no more pages
        page += 1

    logger.info(
        "Fetched %d commits for %s/%s (requested %d)",
        len(collected), owner, repo, total,
    )
    return collected[:total]


def fetch_file_content(
    owner: str,
    repo: str,
    path: str,
    ref: str,
    token: Optional[str] = None,
) -> Optional[str]:
    """
    Fetch the raw content of a single file at a specific commit ref.

    Uses the GitHub Contents API with ``?ref=<sha>`` so we get the exact
    version of the file as it existed in the commit.

    Returns the decoded text content, or ``None`` if the file cannot be
    fetched (binary, too large, not found, etc.).
    """
    import base64

    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    logger.debug("Fetching file content %s/%s:%s @ %s", owner, repo, path, ref[:7])
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                url,
                headers=_default_headers(token),
                params={"ref": ref},
            )
            resp.raise_for_status()
            data = resp.json()

            # GitHub returns base64-encoded content for files < 1 MB
            encoding = data.get("encoding", "")
            content = data.get("content", "")

            if encoding == "base64" and content:
                try:
                    return base64.b64decode(content).decode("utf-8", errors="replace")
                except Exception:
                    return None
            return None
    except httpx.HTTPStatusError:
        return None  # file not found or too large — non-fatal
    except httpx.RequestError as exc:
        logger.warning("Could not fetch file %s: %s", path, exc)
        return None


def fetch_commit_files_content(
    owner: str,
    repo: str,
    sha: str,
    token: Optional[str] = None,
    max_files: int = 20,
) -> list[tuple[str, str]]:
    """
    For a given commit, fetch the source content of each changed file.

    This first calls :func:`fetch_commit_detail` to get the list of modified
    files, then fetches each file's content at the commit ref.

    Args:
        owner / repo:  Repository coordinates.
        sha:           Commit SHA.
        token:         GitHub PAT.
        max_files:     Cap on how many files to download (to avoid API abuse).

    Returns:
        List of ``(filename, source_content)`` tuples.
    """
    try:
        detail = fetch_commit_detail(owner, repo, sha, token=token)
    except Exception as exc:
        logger.warning("Could not fetch commit detail for %s: %s", sha[:7], exc)
        return []

    files_meta = detail.get("files", [])
    results: list[tuple[str, str]] = []

    for fm in files_meta[:max_files]:
        filename = fm.get("filename", "")
        status = fm.get("status", "")

        # Skip removed files — nothing to analyse
        if status == "removed":
            continue

        # Try to use the patch (diff) content directly if the full file is
        # too expensive to fetch.  For complexity analysis we need full source,
        # so we fetch it.
        content = fetch_file_content(owner, repo, filename, ref=sha, token=token)
        if content is not None:
            results.append((filename, content))

    logger.info(
        "Fetched content for %d / %d files in commit %s",
        len(results), len(files_meta), sha[:7],
    )
    return results
