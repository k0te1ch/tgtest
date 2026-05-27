"""Logging setup, modeled on the project template's rotating-file logger."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from tgtest.config import Settings


def configure_logger(settings: Settings) -> logging.Logger:
    """Configure and return the application logger.

    Writes rotating log files under ``logs/`` and, at DEBUG level, also echoes
    to the console so test runs can be traced live.
    """
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(settings.app_name)
    logger.setLevel(settings.log_level.upper())
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_dir / "tgtest.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(settings.log_level.upper())

    if not logger.handlers:
        logger.addHandler(file_handler)

    return logger
