"""Lightweight logging helpers for the stock analysis component."""

from __future__ import annotations

import logging
from typing import Optional


DEFAULT_LOG_FORMAT = "[%(levelname)s] %(name)s: %(message)s"


def configure_logging(level: int = logging.INFO, fmt: str = DEFAULT_LOG_FORMAT) -> None:
    """Configure root logging once for local CLI usage."""

    root_logger = logging.getLogger()
    if root_logger.handlers:
        root_logger.setLevel(level)
        return

    logging.basicConfig(level=level, format=fmt)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a module logger."""

    return logging.getLogger(name or "stock_core")
