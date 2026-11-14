"""Rotating log handler for the headless MTProto bridge."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler


def build_log_handler(
    path: str, log_max_mb: float = 5, backups: int = 1
) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        path,
        maxBytes=max(32 * 1024, int(log_max_mb * 1024 * 1024)),
        backupCount=max(1, int(backups)),
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-5s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    return handler
