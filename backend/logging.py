"""Loguru configuration.

Call `configure_logging()` once at process startup.
"""
from __future__ import annotations

import sys

from loguru import logger

from backend.config import settings


def configure_logging() -> None:
    """Set up loguru sinks. Replace stderr default with a structured sink."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        backtrace=False,
        diagnose=False,
    )
    logger.add(
        "logs/guardian.log",
        level=settings.log_level,
        rotation="50 MB",
        retention="7 days",
        serialize=True,  # structured JSON for ingest
    )
