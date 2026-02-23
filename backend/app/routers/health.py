from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.database import SessionLocal
from app.schemas import HealthResponse

# Import the module-level start time set in main.py.
# We use a lazy import inside the handler to avoid a circular reference at
# module load time (main imports this router; this router imports main).
import importlib

router = APIRouter(prefix="/health", tags=["Health"])
settings = get_settings()


def _db_status() -> str:
    """Return 'ok' if the database is reachable, 'unreachable' otherwise."""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return "ok"
    except Exception:
        return "unreachable"


@router.get("", response_model=HealthResponse)
def health_check():
    """
    Returns service health status for uptime monitoring.

    Checks:
    - API liveness
    - Database connectivity
    - Uptime since process start
    """
    main_module = importlib.import_module("app.main")
    start_time: float = getattr(main_module, "APP_START_TIME", 0.0)

    import time
    uptime = round(time.time() - start_time, 3)

    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
        uptime_seconds=uptime,
        db_status=_db_status(),
    )
