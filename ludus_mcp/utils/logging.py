"""Logging configuration."""

import logging
import sys
from typing import Any

from .config import get_settings


class UserFriendlyFormatter(logging.Formatter):
    """Formatter that produces clean, user-friendly log messages."""

    # Simplified format for INFO and below
    SIMPLE_FORMAT = "%(message)s"
    # Detailed format for WARNING and above
    DETAILED_FORMAT = "%(levelname)s: %(message)s"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record based on level."""
        if record.levelno <= logging.INFO:
            formatter = logging.Formatter(self.SIMPLE_FORMAT)
        else:
            formatter = logging.Formatter(self.DETAILED_FORMAT)
        return formatter.format(record)


def setup_logging(quiet: bool = False) -> None:
    """Configure application logging with user-friendly output.

    Args:
        quiet: Suppress everything below WARNING. Callers decide this
            explicitly (the server is quiet by default and only turns logging
            up for --verbose/--daemon), so no stdio-detection guesswork here.
    """
    settings = get_settings()

    if quiet:
        log_level = logging.WARNING
    else:
        log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Create handler with user-friendly formatter
    handler = logging.StreamHandler(sys.stderr)  # Use stderr for logs
    handler.setFormatter(UserFriendlyFormatter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = [handler]

    # Suppress verbose logs from dependencies
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module."""
    return logging.getLogger(name)

