"""
BigEye Pro — Logger
"""
import logging
import os
from core.config import DEBUG_LOG_PATH


def setup_logger(name: str = "bigeye") -> logging.Logger:
    """Setup application logger with file and console handlers."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # File handler
    os.makedirs(os.path.dirname(DEBUG_LOG_PATH), exist_ok=True)
    fh = logging.FileHandler(DEBUG_LOG_PATH, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    return logger
