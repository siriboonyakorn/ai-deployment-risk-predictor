from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

settings = get_settings()

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {"pool_pre_ping": True}
if _is_sqlite:
    # SQLite requires check_same_thread=False for FastAPI's thread-per-request model
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10

    # Neon serverless requires SSL; psycopg honours sslmode in the DSN,
    # but we also pass connect_args so the pool-level connections behave.
    connect_args: dict = {}
    if "neon.tech" in settings.DATABASE_URL:
        connect_args["sslmode"] = "require"
    if connect_args:
        _engine_kwargs["connect_args"] = connect_args

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
