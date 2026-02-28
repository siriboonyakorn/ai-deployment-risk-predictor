"""
Centralised logging configuration.

Call ``setup_logging()`` once during application startup (in ``main.py``).
Every module should then obtain its logger via::

    import logging
    logger = logging.getLogger(__name__)

The log level is driven by the ``LOG_LEVEL`` setting in config.
"""

from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """
    Configure the root logger with a structured console formatter.

    Args:
        level: Logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(numeric_level)

    # Prevent duplicate handlers when lifespan is re-entered (e.g. tests)
    root.handlers.clear()
    root.addHandler(console_handler)

    # Quiet down noisy third-party loggers unless we're in DEBUG mode
    if numeric_level > logging.DEBUG:
        for name in ("httpx", "httpcore", "urllib3", "sqlalchemy.engine"):
            logging.getLogger(name).setLevel(logging.WARNING)

    logging.getLogger("app").info(
        "Logging configured — level=%s", level,
    )
