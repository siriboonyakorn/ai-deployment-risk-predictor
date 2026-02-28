"""
Failure labeling module  (AI_Model_Engineering.md §3).

Detects whether a commit introduced a production failure by checking four
conditions against the GitHub API:

1. Pull request reverted within 7 days
2. Hotfix commit within 48 hours
3. Issue labeled "bug" referencing the commit
4. Rollback commit detected

Each commit receives a binary label:
    0 → Safe
    1 → Risky  (introduced a failure)

This labeled data becomes the training target for the ML model.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.services.github import _default_headers, GITHUB_API

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Patterns for detecting hotfix / rollback commits
# ---------------------------------------------------------------------------

_HOTFIX_PATTERNS = re.compile(
    r"\b(hotfix|hot[\s-]?fix|emergency[\s-]?fix|critical[\s-]?fix|urgent[\s-]?fix)\b",
    re.IGNORECASE,
)

_ROLLBACK_PATTERNS = re.compile(
    r"\b(revert|rollback|roll[\s-]?back|undo|backed[\s-]?out)\b",
    re.IGNORECASE,
)

_REVERT_SHA_PATTERN = re.compile(
    r"revert(?:s|ing)?\s+(?:commit\s+)?([0-9a-f]{7,40})",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Individual failure detectors
# ---------------------------------------------------------------------------

def detect_hotfix_after(
    owner: str,
    repo: str,
    sha: str,
    committed_at: datetime,
    token: Optional[str] = None,
    window_hours: int = 48,
) -> bool:
    """
    Check if a hotfix commit appeared within *window_hours* after `sha`.

    Looks at the next 30 commits after the target and checks messages for
    hotfix patterns.
    """
    since = committed_at.isoformat()
    until = (committed_at + timedelta(hours=window_hours)).isoformat()

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/commits",
                headers=_default_headers(token),
                params={"since": since, "until": until, "per_page": 30},
            )
            resp.raise_for_status()
            commits = resp.json()
    except Exception as exc:
        logger.warning("Failed to check hotfix commits for %s: %s", sha[:7], exc)
        return False

    for c in commits:
        c_sha = c.get("sha", "")
        if c_sha == sha:
            continue
        msg = (c.get("commit", {}).get("message") or "").strip()
        if _HOTFIX_PATTERNS.search(msg):
            logger.debug("Hotfix detected after %s: %s %s", sha[:7], c_sha[:7], msg[:60])
            return True
    return False


def detect_revert(
    owner: str,
    repo: str,
    sha: str,
    committed_at: datetime,
    token: Optional[str] = None,
    window_days: int = 7,
) -> bool:
    """
    Check if a revert / rollback commit referencing `sha` appeared within
    *window_days*.
    """
    since = committed_at.isoformat()
    until = (committed_at + timedelta(days=window_days)).isoformat()

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/commits",
                headers=_default_headers(token),
                params={"since": since, "until": until, "per_page": 50},
            )
            resp.raise_for_status()
            commits = resp.json()
    except Exception as exc:
        logger.warning("Failed to check revert commits for %s: %s", sha[:7], exc)
        return False

    short_sha = sha[:7]
    for c in commits:
        c_sha = c.get("sha", "")
        if c_sha == sha:
            continue
        msg = (c.get("commit", {}).get("message") or "").strip()

        # Check for revert patterns AND if the message references our SHA
        if _ROLLBACK_PATTERNS.search(msg):
            if short_sha in msg or sha in msg:
                logger.debug("Revert found for %s in commit %s", sha[:7], c_sha[:7])
                return True
            # GitHub auto-generated revert messages: 'Revert "original message"'
            m = _REVERT_SHA_PATTERN.search(msg)
            if m and m.group(1).startswith(short_sha):
                return True
    return False


def detect_bug_issues(
    owner: str,
    repo: str,
    sha: str,
    token: Optional[str] = None,
) -> bool:
    """
    Check if any issue labeled "bug" references the commit SHA.

    Uses the GitHub Search Issues API to find issues mentioning the SHA.
    """
    query = f"repo:{owner}/{repo} {sha[:10]} label:bug"
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{GITHUB_API}/search/issues",
                headers=_default_headers(token),
                params={"q": query, "per_page": 5},
            )
            resp.raise_for_status()
            data = resp.json()
            count = data.get("total_count", 0)
            if count > 0:
                logger.debug("Bug issue found referencing %s (%d results)", sha[:7], count)
                return True
    except Exception as exc:
        logger.warning("Failed to search bug issues for %s: %s", sha[:7], exc)
    return False


def detect_rollback_in_message(commit_message: Optional[str]) -> bool:
    """
    Simple local check — does the commit message itself indicate it's a
    revert or rollback?  (No API call needed.)
    """
    if not commit_message:
        return False
    return bool(_ROLLBACK_PATTERNS.search(commit_message))


# ---------------------------------------------------------------------------
# Aggregate labeler
# ---------------------------------------------------------------------------

def label_commit(
    owner: str,
    repo: str,
    sha: str,
    committed_at: datetime,
    commit_message: Optional[str] = None,
    token: Optional[str] = None,
    check_github: bool = True,
) -> dict:
    """
    Apply all failure-detection heuristics to a single commit and return a
    labeling result.

    Args:
        owner / repo:    Repository coordinates.
        sha:             Full commit SHA.
        committed_at:    Timestamp of the commit.
        commit_message:  The commit message text.
        token:           GitHub PAT for API calls.
        check_github:    When ``False``, skip GitHub API calls (faster, for
                         offline labeling using only local data).

    Returns:
        A dict with::

            {
                "sha": "abc1234...",
                "label": 0 | 1,           # binary target
                "reasons": ["hotfix_48h", ...],
                "checks": {
                    "is_revert": bool,
                    "hotfix_within_48h": bool,
                    "bug_issue_found": bool,
                    "rollback_in_message": bool,
                },
            }
    """
    checks = {
        "is_revert": False,
        "hotfix_within_48h": False,
        "bug_issue_found": False,
        "rollback_in_message": detect_rollback_in_message(commit_message),
    }

    if check_github:
        checks["hotfix_within_48h"] = detect_hotfix_after(
            owner, repo, sha, committed_at, token=token,
        )
        checks["is_revert"] = detect_revert(
            owner, repo, sha, committed_at, token=token,
        )
        checks["bug_issue_found"] = detect_bug_issues(
            owner, repo, sha, token=token,
        )

    # Assemble reasons
    reasons: list[str] = []
    if checks["is_revert"]:
        reasons.append("reverted_within_7d")
    if checks["hotfix_within_48h"]:
        reasons.append("hotfix_within_48h")
    if checks["bug_issue_found"]:
        reasons.append("bug_issue_reference")
    if checks["rollback_in_message"]:
        reasons.append("rollback_in_message")

    label = 1 if reasons else 0

    logger.info(
        "Label for %s: %d  reasons=%s",
        sha[:7], label, reasons or "(safe)",
    )

    return {
        "sha": sha,
        "label": label,
        "reasons": reasons,
        "checks": checks,
    }


def label_commits_batch(
    owner: str,
    repo: str,
    commits: list[dict],
    token: Optional[str] = None,
    check_github: bool = True,
) -> list[dict]:
    """
    Label a batch of commits.

    Args:
        commits: List of dicts with at least ``sha``, ``committed_at``
                 (datetime), and optionally ``message``.

    Returns:
        List of labeling result dicts (same order as input).
    """
    results = []
    for c in commits:
        result = label_commit(
            owner=owner,
            repo=repo,
            sha=c["sha"],
            committed_at=c["committed_at"],
            commit_message=c.get("message"),
            token=token,
            check_github=check_github,
        )
        results.append(result)
    return results
