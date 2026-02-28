"""
Service layer for synchronising commit history from GitHub into the local
database, including per-commit metrics (lines added / deleted, files changed).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.exceptions import AppError, ExternalServiceError, NotFoundError
from app.models import Commit, Repository
from app.services.github import (
    fetch_commit_detail,
    fetch_commits_paginated,
)

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def sync_commits_for_repo(
    repo: Repository,
    db: Session,
    *,
    branch: Optional[str] = None,
    limit: Optional[int] = None,
    fetch_metrics: bool = True,
) -> list[Commit]:
    """
    Fetch up to *limit* recent commits from GitHub and upsert them into the
    database.  For each **new** commit the per-commit detail endpoint is
    called to populate ``lines_added``, ``lines_deleted`` and
    ``files_changed``.

    Args:
        repo:           Repository ORM object (must have ``full_name``).
        db:             Active SQLAlchemy session.
        branch:         Branch to query (``None`` → default branch).
        limit:          Max commits to fetch.  Falls back to
                        ``settings.COMMIT_FETCH_LIMIT`` (default 100).
        fetch_metrics:  If ``True``, hit the single-commit endpoint for
                        stats.  Set to ``False`` to skip (faster, but no
                        lines-added / deleted data).

    Returns:
        List of ``Commit`` ORM objects that were created **or** updated.
    """
    limit = limit or settings.COMMIT_FETCH_LIMIT
    parts = repo.full_name.split("/", 1)
    if len(parts) != 2:
        raise NotFoundError("Repository", repo.full_name)
    owner, repo_name = parts
    token = settings.github_token_or_none

    logger.info(
        "Starting commit sync for %s (branch=%s, limit=%d, metrics=%s)",
        repo.full_name, branch, limit, fetch_metrics,
    )

    # 1. Fetch commit list (paginated)
    try:
        raw_commits = fetch_commits_paginated(
            owner, repo_name, token=token, branch=branch, total=limit,
        )
    except AppError:
        raise  # already translated
    except Exception as exc:
        raise ExternalServiceError("GitHub", str(exc))

    upserted: list[Commit] = []

    for raw in raw_commits:
        sha: str = raw.get("sha", "")
        if not sha:
            continue

        # Check if commit already exists
        existing = db.query(Commit).filter(
            Commit.sha == sha,
            Commit.repository_id == repo.id,
        ).first()

        if existing:
            upserted.append(existing)
            continue

        inner = raw.get("commit", {})
        author_info = inner.get("author") or {}
        committed_at = _parse_iso(author_info.get("date"))

        commit = Commit(
            sha=sha,
            message=inner.get("message", ""),
            author_name=author_info.get("name"),
            author_email=author_info.get("email"),
            committed_at=committed_at,
            repository_id=repo.id,
        )

        # 2. Fetch per-commit stats (lines added / deleted / files changed)
        if fetch_metrics:
            try:
                detail = fetch_commit_detail(owner, repo_name, sha, token=token)
                stats = detail.get("stats", {})
                commit.lines_added = stats.get("additions", 0)
                commit.lines_deleted = stats.get("deletions", 0)
                commit.files_changed = len(detail.get("files", []))
                logger.debug(
                    "  %s  +%d  -%d  files=%d",
                    sha[:7], commit.lines_added, commit.lines_deleted, commit.files_changed,
                )
            except Exception as exc:
                # Non-fatal: log and continue with zeroes
                logger.warning("Could not fetch stats for %s: %s", sha[:7], exc)

        db.add(commit)
        upserted.append(commit)

    db.commit()

    new_count = sum(1 for c in upserted if c.id is None or c.created_at is None)
    logger.info(
        "Commit sync complete for %s — %d fetched, %d new records persisted.",
        repo.full_name, len(raw_commits), len(upserted),
    )
    return upserted


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    """Best-effort ISO-8601 parse, returning None on failure."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
