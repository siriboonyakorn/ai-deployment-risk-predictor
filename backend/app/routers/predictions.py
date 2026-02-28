import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.exceptions import NotFoundError
from app.models import Commit, Repository, RiskAssessment, RiskLevel
from app.schemas import RiskPredictionRequest, RiskPredictionResponse
from app.ml.predictor import predictor
from app.services.code_analysis import analyse_commit_files, is_radon_available
from app.services.github import fetch_commit_files_content
from app.services.risk_engine import calculate_risk, extract_features

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predictions", tags=["Predictions"])
settings = get_settings()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_developer_stats(
    db: Session,
    author_email: Optional[str],
    repository_id: int,
) -> dict:
    """
    Query the database for developer-level features used by the risk engine.

    Returns a dict with keys matching :func:`extract_features` kwargs:
    ``total_prior_commits``, ``previous_bug_rate``, ``commit_frequency``,
    ``time_since_last_commit``.
    """
    result = {
        "total_prior_commits": 0,
        "previous_bug_rate": 0.0,
        "commit_frequency": 0.0,
        "time_since_last_commit": 0.0,
    }

    if not author_email:
        return result

    # Count prior commits by this author in this repository
    prior_commits = (
        db.query(Commit)
        .filter(
            Commit.author_email == author_email,
            Commit.repository_id == repository_id,
        )
        .all()
    )
    result["total_prior_commits"] = len(prior_commits)

    if not prior_commits:
        return result

    # Calculate previous bug rate (commits that had HIGH risk / total)
    risky_count = 0
    for c in prior_commits:
        if c.risk_assessment and c.risk_assessment.risk_level == RiskLevel.HIGH:
            risky_count += 1
    result["previous_bug_rate"] = round(risky_count / len(prior_commits), 4) if prior_commits else 0.0

    # Commit frequency (commits in last 30 days / 30)
    from datetime import timedelta, timezone as tz
    now = datetime.now(tz.utc)
    recent = [
        c for c in prior_commits
        if c.committed_at and (now - c.committed_at.replace(tzinfo=tz.utc)).days <= 30
    ]
    result["commit_frequency"] = round(len(recent) / 30.0, 4)

    # Time since last commit (hours)
    dates = [c.committed_at for c in prior_commits if c.committed_at]
    if dates:
        latest = max(dates)
        delta = now - latest.replace(tzinfo=tz.utc)
        result["time_since_last_commit"] = round(delta.total_seconds() / 3600, 2)

    return result


def _get_repo_stats(db: Session, repository_id: int) -> dict:
    """
    Query the database for repository-level features.

    Returns dict matching :func:`extract_features` kwargs.
    """
    commit_count = db.query(Commit).filter(Commit.repository_id == repository_id).count()
    # Distinct authors as a proxy for contributor count
    authors = (
        db.query(Commit.author_email)
        .filter(
            Commit.repository_id == repository_id,
            Commit.author_email.isnot(None),
        )
        .distinct()
        .count()
    )
    return {
        "contributor_count": authors,
        "commit_velocity": round(commit_count / 4.0, 2),  # approx commits/week
    }


# ---------------------------------------------------------------------------
# POST /predictions — analyse a commit
# ---------------------------------------------------------------------------

@router.post("", response_model=RiskPredictionResponse, status_code=status.HTTP_201_CREATED)
def predict_risk(payload: RiskPredictionRequest, db: Session = Depends(get_db)):
    """
    Analyse a commit and return its risk assessment.

    Steps:
    1. Upsert the commit record.
    2. (Optional) Fetch changed files from GitHub and run radon complexity
       analysis.
    3. Extract all ML features (code-level, developer, temporal, derived).
    4. Compute rule-based risk score.
    5. Persist the assessment with full features JSON for future ML training.
    """
    repo = db.query(Repository).filter(
        Repository.full_name == payload.repository_full_name
    ).first()

    if not repo:
        raise NotFoundError("Repository", payload.repository_full_name)

    # ── 1. Upsert commit ──────────────────────────────────────────────
    commit = db.query(Commit).filter(
        Commit.sha == payload.sha,
        Commit.repository_id == repo.id,
    ).first()

    if not commit:
        commit = Commit(
            sha=payload.sha,
            message=payload.commit_message,
            author_email=payload.author_email,
            lines_added=payload.lines_added,
            lines_deleted=payload.lines_deleted,
            files_changed=payload.files_changed,
            repository_id=repo.id,
        )
        db.add(commit)
        db.flush()

    # ── 2. Complexity analysis (radon) ─────────────────────────────────
    complexity_report = None
    changed_files: list[tuple[str, str]] = []

    if payload.analyze_complexity and is_radon_available():
        parts = repo.full_name.split("/", 1)
        if len(parts) == 2:
            owner, repo_name = parts
            token = settings.github_token_or_none
            changed_files = fetch_commit_files_content(
                owner, repo_name, payload.sha, token=token, max_files=20,
            )
            if changed_files:
                complexity_report = analyse_commit_files(payload.sha, changed_files)

                # Persist complexity on the commit record
                commit.avg_cyclomatic_complexity = complexity_report.avg_cyclomatic_complexity
                commit.max_cyclomatic_complexity = complexity_report.max_cyclomatic_complexity
                commit.avg_maintainability_index = complexity_report.avg_maintainability_index
                commit.complexity_rank = complexity_report.overall_cc_rank

    # ── 3. Developer & repo stats ──────────────────────────────────────
    dev_stats = _get_developer_stats(db, payload.author_email, repo.id)
    repo_stats = _get_repo_stats(db, repo.id)

    # ── 4. Extract features ────────────────────────────────────────────
    features = extract_features(
        lines_added=payload.lines_added,
        lines_deleted=payload.lines_deleted,
        files_changed=payload.files_changed,
        commit_message=payload.commit_message,
        committed_at=commit.committed_at,
        author_email=payload.author_email,
        changed_files=changed_files or None,
        complexity_report=complexity_report,
        **dev_stats,
        **repo_stats,
    )

    # ── 5. Calculate risk score (ML model if available, else rule-based) ─
    result = predictor.predict(features)

    # ── 6. Upsert assessment ──────────────────────────────────────────
    assessment = db.query(RiskAssessment).filter(
        RiskAssessment.commit_id == commit.id
    ).first()

    features_json = features.to_json()
    breakdown_json = json.dumps(result.score_breakdown)

    if assessment:
        assessment.risk_score = result.risk_score
        assessment.risk_level = result.risk_level
        assessment.confidence = result.confidence
        assessment.features_json = features_json
        assessment.score_breakdown_json = breakdown_json
        assessment.model_version = predictor.version
    else:
        assessment = RiskAssessment(
            commit_id=commit.id,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            confidence=result.confidence,
            features_json=features_json,
            score_breakdown_json=breakdown_json,
            model_version=predictor.version,
        )
        db.add(assessment)

    db.commit()
    db.refresh(commit)
    db.refresh(assessment)

    logger.info(
        "Risk prediction for %s: score=%.1f level=%s confidence=%.2f",
        payload.sha[:7], result.risk_score, result.risk_level.value, result.confidence,
    )
    return RiskPredictionResponse(commit=commit, assessment=assessment)


# ---------------------------------------------------------------------------
# GET /predictions — list all assessments
# ---------------------------------------------------------------------------

@router.get("", response_model=list[RiskPredictionResponse])
def list_predictions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List all risk assessments, newest first."""
    assessments = (
        db.query(RiskAssessment)
        .order_by(RiskAssessment.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        RiskPredictionResponse(commit=a.commit, assessment=a)
        for a in assessments
        if a.commit
    ]


# ---------------------------------------------------------------------------
# GET /predictions/complexity-status — check radon availability
# ---------------------------------------------------------------------------

@router.get("/complexity-status")
def complexity_status():
    """Check whether radon complexity analysis is available."""
    return {
        "radon_available": is_radon_available(),
        "message": (
            "Radon is installed and ready for complexity analysis."
            if is_radon_available()
            else "Radon is not installed. Install with: pip install radon"
        ),
    }


# ---------------------------------------------------------------------------
# GET /predictions/model-info — ML model status
# ---------------------------------------------------------------------------

@router.get("/model-info")
def model_info():
    """
    Return information about the currently loaded prediction engine.

    Reports whether the ML model is active or if the rule-based fallback
    is being used.
    """
    return predictor.get_info()


# ---------------------------------------------------------------------------
# GET /predictions/{commit_sha} — single assessment  (must be LAST)
# ---------------------------------------------------------------------------

@router.get("/{commit_sha}", response_model=RiskPredictionResponse)
def get_prediction(commit_sha: str, db: Session = Depends(get_db)):
    """Retrieve an existing risk assessment by commit SHA."""
    commit = db.query(Commit).filter(Commit.sha == commit_sha).first()

    if not commit or not commit.risk_assessment:
        raise NotFoundError("Risk assessment", commit_sha)

    return RiskPredictionResponse(commit=commit, assessment=commit.risk_assessment)
