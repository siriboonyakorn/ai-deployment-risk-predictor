"""
Background Celery tasks for asynchronous commit risk analysis.

These tasks are enqueued by the webhook handler or the sync endpoint
so that the HTTP response returns immediately while the heavy lifting
(GitHub file fetching, radon complexity, ML prediction) happens in the
worker process.
"""

import json
import logging

from app.celery_app import celery
from app.config import get_settings
from app.database import SessionLocal
from app.models import Commit, RiskAssessment, RiskLevel
from app.ml.predictor import predictor
from app.services.code_analysis import analyse_commit_files, is_radon_available
from app.services.github import fetch_commit_files_content
from app.services.risk_engine import extract_features

logger = logging.getLogger(__name__)
settings = get_settings()


@celery.task(
    name="analyze_commit",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def analyze_commit(self, commit_id: int, repo_full_name: str) -> dict:
    """
    Run the full risk-analysis pipeline for a single commit.

    1. Fetch changed files from GitHub.
    2. Run radon complexity analysis on Python files.
    3. Extract ML features.
    4. Score with the ML model (fallback to rule-based).
    5. Persist the ``RiskAssessment`` row.

    Parameters
    ----------
    commit_id : int
        Primary key of the :class:`Commit` row.
    repo_full_name : str
        ``"owner/repo"`` string used to call the GitHub API.

    Returns
    -------
    dict
        ``{"commit_id": …, "risk_score": …, "risk_level": …}``
    """
    db = SessionLocal()
    try:
        commit = db.query(Commit).filter(Commit.id == commit_id).first()
        if not commit:
            logger.warning("analyze_commit: commit %d not found", commit_id)
            return {"error": "commit not found"}

        # ── 1. Fetch source files ─────────────────────────────────────
        complexity_report = None
        changed_files: list[tuple[str, str]] = []

        if is_radon_available():
            parts = repo_full_name.split("/", 1)
            if len(parts) == 2:
                owner, repo_name = parts
                token = settings.github_token_or_none
                try:
                    changed_files = fetch_commit_files_content(
                        owner, repo_name, commit.sha,
                        token=token, max_files=20,
                    )
                except Exception as exc:
                    logger.warning(
                        "Could not fetch files for %s: %s", commit.sha[:7], exc,
                    )

                if changed_files:
                    complexity_report = analyse_commit_files(
                        commit.sha, changed_files,
                    )
                    commit.avg_cyclomatic_complexity = complexity_report.avg_cyclomatic_complexity
                    commit.max_cyclomatic_complexity = complexity_report.max_cyclomatic_complexity
                    commit.avg_maintainability_index = complexity_report.avg_maintainability_index
                    commit.complexity_rank = complexity_report.overall_cc_rank

        # ── 2. Extract features ───────────────────────────────────────
        features = extract_features(
            lines_added=commit.lines_added or 0,
            lines_deleted=commit.lines_deleted or 0,
            files_changed=commit.files_changed or 0,
            commit_message=commit.message,
            committed_at=commit.committed_at,
            author_email=commit.author_email,
            changed_files=changed_files or None,
            complexity_report=complexity_report,
        )

        # ── 3. Predict ────────────────────────────────────────────────
        result = predictor.predict(features)

        # ── 4. Persist assessment ─────────────────────────────────────
        features_json = features.to_json()
        breakdown_json = json.dumps(result.score_breakdown)

        assessment = (
            db.query(RiskAssessment)
            .filter(RiskAssessment.commit_id == commit.id)
            .first()
        )

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

        logger.info(
            "Async analysis complete for %s: score=%.1f level=%s",
            commit.sha[:7], result.risk_score, result.risk_level,
        )
        return {
            "commit_id": commit.id,
            "risk_score": result.risk_score,
            "risk_level": result.risk_level,
        }

    except Exception as exc:
        db.rollback()
        logger.exception("analyze_commit failed for commit_id=%d", commit_id)
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery.task(name="analyze_commits_batch")
def analyze_commits_batch(commit_ids: list[int], repo_full_name: str) -> dict:
    """
    Enqueue individual ``analyze_commit`` tasks for a batch of commits.

    Useful after a bulk sync — fire-and-forget from the HTTP handler,
    and each commit is processed independently in the worker pool.
    """
    for cid in commit_ids:
        analyze_commit.delay(cid, repo_full_name)

    logger.info(
        "Batch enqueued %d commit analysis tasks for %s",
        len(commit_ids), repo_full_name,
    )
    return {"enqueued": len(commit_ids), "repo": repo_full_name}
