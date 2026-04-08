"""Application logging configuration."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from backend.app.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure process-wide application logging."""
    logger.remove()

    if settings.LOG_STDOUT:
        logger.add(sys.stdout, level=settings.LOG_LEVEL.value, backtrace=True, diagnose=True)

    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger.add(
        settings.LOG_DIR / "app.log",
        level=settings.LOG_LEVEL.value,
        backtrace=True,
        diagnose=True,
        rotation="10 MB",
        retention=5,
    )
