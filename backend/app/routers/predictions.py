import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import NotFoundError
from app.models import Commit, Repository, RiskAssessment, RiskLevel
from app.schemas import RiskPredictionRequest, RiskPredictionResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predictions", tags=["Predictions"])


def _calculate_risk(
    lines_added: int,
    lines_deleted: int,
    files_changed: int,
    commit_message: str | None,
) -> tuple[float, RiskLevel, float]:
    """
    Simple rule-based risk scorer (MVP).
    Returns (risk_score 0-100, risk_level, confidence).
    Will be replaced by ML model in a later milestone.
    """
    score = 0.0

    # Lines changed
    total_lines = lines_added + lines_deleted
    if total_lines > 500:
        score += 40.0
    elif total_lines > 200:
        score += 25.0
    elif total_lines > 50:
        score += 10.0

    # Files changed
    if files_changed > 20:
        score += 30.0
    elif files_changed > 10:
        score += 15.0
    elif files_changed > 5:
        score += 8.0

    # Commit message heuristics
    if commit_message:
        risky_keywords = ["fix", "hotfix", "urgent", "hack", "workaround", "temp", "wip"]
        msg_lower = commit_message.lower()
        if any(kw in msg_lower for kw in risky_keywords):
            score += 15.0

    score = min(score, 100.0)

    if score >= 60:
        level = RiskLevel.HIGH
    elif score >= 30:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    confidence = 0.75  # fixed confidence for rule-based MVP

    return round(score, 2), level, confidence


@router.post("", response_model=RiskPredictionResponse, status_code=status.HTTP_201_CREATED)
def predict_risk(payload: RiskPredictionRequest, db: Session = Depends(get_db)):
    """Analyse a commit and return its risk assessment."""
    repo = db.query(Repository).filter(
        Repository.full_name == payload.repository_full_name
    ).first()

    if not repo:
        raise NotFoundError("Repository", payload.repository_full_name)

    # Upsert commit
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

    # Calculate risk
    risk_score, risk_level, confidence = _calculate_risk(
        lines_added=payload.lines_added,
        lines_deleted=payload.lines_deleted,
        files_changed=payload.files_changed,
        commit_message=payload.commit_message,
    )

    # Upsert assessment
    assessment = db.query(RiskAssessment).filter(
        RiskAssessment.commit_id == commit.id
    ).first()

    if assessment:
        assessment.risk_score = risk_score
        assessment.risk_level = risk_level
        assessment.confidence = confidence
    else:
        assessment = RiskAssessment(
            commit_id=commit.id,
            risk_score=risk_score,
            risk_level=risk_level,
            confidence=confidence,
        )
        db.add(assessment)

    db.commit()
    db.refresh(commit)
    db.refresh(assessment)

    logger.info(
        "Risk prediction for %s: score=%.1f level=%s",
        payload.sha[:7], risk_score, risk_level.value,
    )
    return RiskPredictionResponse(commit=commit, assessment=assessment)


@router.get("/{commit_sha}", response_model=RiskPredictionResponse)
def get_prediction(commit_sha: str, db: Session = Depends(get_db)):
    """Retrieve an existing risk assessment by commit SHA."""
    commit = db.query(Commit).filter(Commit.sha == commit_sha).first()

    if not commit or not commit.risk_assessment:
        raise NotFoundError("Risk assessment", commit_sha)

    return RiskPredictionResponse(commit=commit, assessment=commit.risk_assessment)
