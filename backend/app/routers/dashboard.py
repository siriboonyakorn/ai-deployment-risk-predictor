"""
Dashboard statistics API router.

Provides aggregated metrics consumed by the frontend dashboard cards
and risk distribution charts.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Commit, Repository, RiskAssessment, RiskLevel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ---------------------------------------------------------------------------
# GET /dashboard/stats — main overview numbers
# ---------------------------------------------------------------------------

@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    """
    Return aggregate statistics for the dashboard overview cards.

    Response shape::

        {
            "total_repositories": int,
            "total_commits": int,
            "total_assessments": int,
            "risk_counts": {"LOW": int, "MEDIUM": int, "HIGH": int},
            "avg_risk_score": float | null,
            "high_risk_count": int,
            "recent_commits_24h": int,
            "recent_high_risk_24h": int,
        }
    """
    total_repos = db.query(func.count(Repository.id)).scalar() or 0
    total_commits = db.query(func.count(Commit.id)).scalar() or 0
    total_assessments = db.query(func.count(RiskAssessment.id)).scalar() or 0

    # Risk level breakdown
    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    rows = (
        db.query(RiskAssessment.risk_level, func.count(RiskAssessment.id))
        .group_by(RiskAssessment.risk_level)
        .all()
    )
    for level, count in rows:
        key = level.value if isinstance(level, RiskLevel) else str(level)
        risk_counts[key] = count

    avg_score = db.query(func.avg(RiskAssessment.risk_score)).scalar()
    high_risk_count = risk_counts.get("HIGH", 0)

    # Last 24 hours
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_commits = (
        db.query(func.count(Commit.id))
        .filter(Commit.created_at >= cutoff)
        .scalar()
    ) or 0
    recent_high = (
        db.query(func.count(RiskAssessment.id))
        .filter(
            RiskAssessment.created_at >= cutoff,
            RiskAssessment.risk_level == RiskLevel.HIGH,
        )
        .scalar()
    ) or 0

    return {
        "total_repositories": total_repos,
        "total_commits": total_commits,
        "total_assessments": total_assessments,
        "risk_counts": risk_counts,
        "avg_risk_score": round(avg_score, 1) if avg_score is not None else None,
        "high_risk_count": high_risk_count,
        "recent_commits_24h": recent_commits,
        "recent_high_risk_24h": recent_high,
    }


# ---------------------------------------------------------------------------
# GET /dashboard/risk-distribution — for pie / bar charts
# ---------------------------------------------------------------------------

@router.get("/risk-distribution")
def risk_distribution(db: Session = Depends(get_db)):
    """
    Return risk distribution data suitable for pie/bar charts.

    Response::

        {
            "distribution": [
                {"level": "LOW",    "count": 42, "percentage": 60.0},
                {"level": "MEDIUM", "count": 21, "percentage": 30.0},
                {"level": "HIGH",   "count":  7, "percentage": 10.0},
            ],
            "total": 70,
            "score_histogram": [...]
        }
    """
    total = db.query(func.count(RiskAssessment.id)).scalar() or 0
    rows = (
        db.query(RiskAssessment.risk_level, func.count(RiskAssessment.id))
        .group_by(RiskAssessment.risk_level)
        .all()
    )

    distribution = []
    for level_name in ("LOW", "MEDIUM", "HIGH"):
        count = 0
        for level, c in rows:
            key = level.value if isinstance(level, RiskLevel) else str(level)
            if key == level_name:
                count = c
        distribution.append({
            "level": level_name,
            "count": count,
            "percentage": round(count / total * 100, 1) if total else 0,
        })

    # Score histogram (buckets of 10)
    buckets = []
    for lo in range(0, 100, 10):
        hi = lo + 10
        label = f"{lo}-{hi}"
        c = (
            db.query(func.count(RiskAssessment.id))
            .filter(RiskAssessment.risk_score >= lo, RiskAssessment.risk_score < hi)
            .scalar()
        ) or 0
        buckets.append({"range": label, "count": c})

    return {
        "distribution": distribution,
        "total": total,
        "score_histogram": buckets,
    }


# ---------------------------------------------------------------------------
# GET /dashboard/recent-activity — latest assessed commits
# ---------------------------------------------------------------------------

@router.get("/recent-activity")
def recent_activity(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Return the most recently analysed commits with their risk data.
    Used by the dashboard activity feed.
    """
    assessments = (
        db.query(RiskAssessment)
        .order_by(RiskAssessment.created_at.desc())
        .limit(limit)
        .all()
    )

    items = []
    for a in assessments:
        c = a.commit
        if not c:
            continue
        repo = c.repository
        items.append({
            "sha": c.sha,
            "message": c.message or "",
            "author_email": c.author_email,
            "author_name": c.author_name,
            "risk_score": a.risk_score,
            "risk_level": a.risk_level.value if isinstance(a.risk_level, RiskLevel) else str(a.risk_level),
            "confidence": a.confidence,
            "model_version": a.model_version,
            "repository_full_name": repo.full_name if repo else None,
            "committed_at": c.committed_at.isoformat() if c.committed_at else None,
            "analyzed_at": a.created_at.isoformat() if a.created_at else None,
        })

    return {"items": items, "count": len(items)}


# ---------------------------------------------------------------------------
# GET /dashboard/commits-with-risk — paginated commit table with risk info
# ---------------------------------------------------------------------------

@router.get("/commits-with-risk")
def commits_with_risk(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    risk_level: str = Query(default=None, description="Filter by risk level: LOW, MEDIUM, HIGH"),
    sort_by: str = Query(default="created_at", description="Sort field: created_at, risk_score, files_changed, lines_added"),
    sort_order: str = Query(default="desc", description="Sort direction: asc, desc"),
    search: str = Query(default=None, description="Search in commit message or SHA"),
    repo_id: int = Query(default=None, description="Filter by repository ID"),
    db: Session = Depends(get_db),
):
    """
    Paginated list of commits with their risk assessments.

    Supports sorting by any numeric field, filtering by risk level,
    searching by message/SHA, and filtering by repository.
    """
    query = db.query(Commit)

    # Filters
    if repo_id:
        query = query.filter(Commit.repository_id == repo_id)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            (Commit.sha.ilike(pattern)) | (Commit.message.ilike(pattern))
        )

    # Join risk assessment for risk-level filter and risk-score sort
    if risk_level and risk_level.upper() in ("LOW", "MEDIUM", "HIGH"):
        query = query.join(RiskAssessment).filter(
            RiskAssessment.risk_level == RiskLevel(risk_level.upper())
        )

    # Sorting
    sort_map = {
        "created_at": Commit.created_at,
        "risk_score": RiskAssessment.risk_score,
        "files_changed": Commit.files_changed,
        "lines_added": Commit.lines_added,
    }
    sort_col = sort_map.get(sort_by, Commit.created_at)

    # If sorting by risk_score, ensure join exists
    if sort_by == "risk_score" and not risk_level:
        query = query.outerjoin(RiskAssessment)

    if sort_order.lower() == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    total = query.count()
    commits = query.offset(skip).limit(limit).all()

    items = []
    for c in commits:
        a = c.risk_assessment
        repo = c.repository
        items.append({
            "id": c.id,
            "sha": c.sha,
            "message": c.message or "",
            "author_name": c.author_name,
            "author_email": c.author_email,
            "lines_added": c.lines_added,
            "lines_deleted": c.lines_deleted,
            "files_changed": c.files_changed,
            "avg_cyclomatic_complexity": c.avg_cyclomatic_complexity,
            "complexity_rank": c.complexity_rank,
            "repository_id": c.repository_id,
            "repository_full_name": repo.full_name if repo else None,
            "committed_at": c.committed_at.isoformat() if c.committed_at else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "risk_score": a.risk_score if a else None,
            "risk_level": (a.risk_level.value if isinstance(a.risk_level, RiskLevel) else str(a.risk_level)) if a else None,
            "confidence": a.confidence if a else None,
            "model_version": a.model_version if a else None,
        })

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }
