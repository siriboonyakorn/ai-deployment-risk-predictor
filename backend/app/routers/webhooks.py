import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Commit, Repository, RiskAssessment
from app.services.risk_engine import extract_features
from app.ml.predictor import predictor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
settings = get_settings()


def _is_celery_available() -> bool:
    """Return True if Redis/Celery is reachable for async task dispatch."""
    try:
        from app.celery_app import celery as celery_app
        conn = celery_app.connection()
        conn.connect()
        conn.close()
        return True
    except Exception:
        return False


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
    async_ids = []  # commit IDs to analyse in background

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
                lines_added=added,
                lines_deleted=removed,
                repository_id=repo.id,
            )
            db.add(commit)
            db.flush()

        # Quick synchronous scoring (instant response)
        features = extract_features(
            commit_message=message,
            files_changed=added + removed + modified,
            lines_added=added,
            lines_deleted=removed,
        )
        pred = predictor.predict(features)
        risk_score = pred["risk_score"]
        risk_level = pred["risk_level"]
        confidence = pred["confidence"]
        model_version = pred.get("model_version", "rule-v1")

        existing = db.query(RiskAssessment).filter(
            RiskAssessment.commit_id == commit.id
        ).first()

        if not existing:
            db.add(RiskAssessment(
                commit_id=commit.id,
                risk_score=risk_score,
                risk_level=risk_level,
                confidence=confidence,
                model_version=model_version,
            ))

        # Collect IDs for deeper async analysis (radon + file fetch)
        async_ids.append(commit.id)

        processed.append({"sha": sha[:7], "risk_score": risk_score, "risk_level": risk_level})

    db.commit()

    # Dispatch background analysis for complexity if Celery is available
    if async_ids and _is_celery_available():
        try:
            from app.tasks.analysis import analyze_commits_batch
            analyze_commits_batch.delay(async_ids, repo_full_name)
            logger.info("Dispatched async analysis for %d commits", len(async_ids))
        except Exception as exc:
            logger.warning("Could not dispatch async tasks: %s", exc)

    logger.info("Webhook processed %d commits for %s", len(processed), repo_full_name)
    return {"message": "Webhook processed.", "commits": processed}
