"""
Celery application factory.

Uses Redis as both broker and result backend.  Configure via the
``REDIS_URL`` environment variable (defaults to ``redis://redis:6379/0``).

Usage (start a worker)::

    celery -A app.celery_app worker --loglevel=info
"""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery = Celery(
    "risk_predictor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery.conf.update(
    # Serialisation -----------------------------------------------------------
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone ----------------------------------------------------------------
    timezone="UTC",
    enable_utc=True,

    # Result expiry -----------------------------------------------------------
    result_expires=3600,  # 1 hour

    # Reliability -------------------------------------------------------------
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Task routing (all tasks go to the default queue) ------------------------
    task_default_queue="risk_analysis",
)

# Auto-discover task modules inside the ``app.tasks`` package.
celery.autodiscover_tasks(["app.tasks"])
