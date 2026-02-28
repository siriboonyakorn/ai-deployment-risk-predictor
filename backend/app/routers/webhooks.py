import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Commit, Repository, RiskAssessment
from app.routers.predictions import _calculate_risk

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
settings = get_settings()


def _verify_signature(payload: bytes, signature: str) -> bool:
    """Validate GitHub HMAC-SHA256 webhook signature."""
    if not settings.GITHUB_WEBHOOK_SECRET:
        logger.debug("GITHUB_WEBHOOK_SECRET not set — skipping signature check")
        return True

    expected = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/github", status_code=status.HTTP_200_OK)
async def github_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: str = Header(default=""),
    x_github_event: str = Header(default=""),
):
    """Receive GitHub webhook events and trigger risk analysis."""
    body = await request.body()

    if not _verify_signature(body, x_hub_signature_256):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature.",
        )

    if x_github_event != "push":
        logger.debug("Ignoring GitHub event: %s", x_github_event)
        return {"message": f"Event '{x_github_event}' ignored."}

    payload = json.loads(body)
    repo_full_name = payload.get("repository", {}).get("full_name", "")
    github_repo_id = payload.get("repository", {}).get("id")
    commits_data = payload.get("commits", [])

    repo = db.query(Repository).filter(Repository.full_name == repo_full_name).first()
    if not repo:
        # Auto-register unknown repo (no owner attached in webhook flow)
        repo = Repository(
            github_repo_id=github_repo_id,
            name=repo_full_name.split("/")[-1],
            full_name=repo_full_name,
            owner_id=1,  # placeholder; proper auth wires this up later
        )
        db.add(repo)
        db.flush()

    processed = []
    for commit_data in commits_data:
        sha = commit_data.get("id", "")
        added = len(commit_data.get("added", []))
        removed = len(commit_data.get("removed", []))
        modified = len(commit_data.get("modified", []))
        message = commit_data.get("message", "")

        commit = db.query(Commit).filter(
            Commit.sha == sha,
            Commit.repository_id == repo.id,
        ).first()

        if not commit:
            commit = Commit(
                sha=sha,
                message=message,
                author_name=commit_data.get("author", {}).get("name"),
                author_email=commit_data.get("author", {}).get("email"),
                files_changed=added + removed + modified,
                repository_id=repo.id,
            )
            db.add(commit)
            db.flush()

        risk_score, risk_level, confidence = _calculate_risk(
            lines_added=added,
            lines_deleted=removed,
            files_changed=added + removed + modified,
            commit_message=message,
        )

        existing = db.query(RiskAssessment).filter(
            RiskAssessment.commit_id == commit.id
        ).first()

        if not existing:
            db.add(RiskAssessment(
                commit_id=commit.id,
                risk_score=risk_score,
                risk_level=risk_level,
                confidence=confidence,
            ))

        processed.append({"sha": sha[:7], "risk_score": risk_score, "risk_level": risk_level})

    db.commit()
    logger.info("Webhook processed %d commits for %s", len(processed), repo_full_name)
    return {"message": "Webhook processed.", "commits": processed}
