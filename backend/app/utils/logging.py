"""
logging.py — Structured application logger

Sets up a consistent logging format for the entire backend.
All modules should import get_logger() instead of using print().
"""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger with a consistent format.

    Usage:
        from app.utils.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger
