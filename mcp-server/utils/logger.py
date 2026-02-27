"""
Centralised logging configuration for MCP Server.

All log output goes to:
  - stdout (INFO+)
  - logs/mcp_server.log (DEBUG+, rotating)
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(_PROJECT_ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "mcp_server.log")

os.makedirs(LOG_DIR, exist_ok=True)

_FORMATTER = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-8s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    """Return (or create) a named logger with console + rotating-file handlers."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Console handler — INFO and above
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(_FORMATTER)
    logger.addHandler(ch)

    # File handler — DEBUG and above, 10 MB × 5 backups
    fh = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(_FORMATTER)
    logger.addHandler(fh)

    return logger
