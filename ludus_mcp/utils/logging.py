"""Logging configuration.

File logging was contributed by LouDeter
(https://github.com/tjnull/Ludus-FastMCP/pull/8).
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any

from .config import get_settings

LOG_FILE = Path.home() / ".ludus-fastmcp" / "ludus-fastmcp.log"

# The middleware logs a payload per request and response, so DEBUG fills a file
# quickly. Cap it rather than letting a long-running daemon grow without bound.
LOG_FILE_MAX_BYTES = 5 * 1024 * 1024
LOG_FILE_BACKUP_COUNT = 3


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


def _build_file_handler(level: int) -> logging.Handler | None:
    """Create the rotating log-file handler, or None if the file is unusable.

    Logging must never be the reason the server fails to start: setup_logging()
    runs at import time, and a read-only home, a full disk or a locked-down
    container would otherwise raise before any tool is registered. If the file
    cannot be opened we simply carry on with stderr.
    """
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_FILE_BACKUP_COUNT,
        )
    except OSError as e:
        print(
            f"WARNING: file logging disabled ({LOG_FILE}: {e}); logging to stderr only",
            file=sys.stderr,
        )
        return None

    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    file_handler.setLevel(level)
    return file_handler


def setup_logging(quiet: bool = False, log_to_file: bool = True) -> None:
    """Configure application logging with user-friendly output.

    Args:
        quiet: Suppress everything below WARNING on stderr. Callers decide this
            explicitly (the server is quiet by default and only turns logging
            up for --verbose/--daemon), so no stdio-detection guesswork here.
        log_to_file: Also write to LOG_FILE. Pass False in daemon mode, where
            stderr is already redirected into that same file with os.dup2(),
            so a file handler would record every line twice.
    """
    settings = get_settings()
    configured_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Quiet applies to stderr only. An MCP client launches the server quietly,
    # so without this split there would be no record of anything to debug with.
    stderr_level = logging.WARNING if quiet else configured_level

    handler = logging.StreamHandler(sys.stderr)  # Use stderr for logs
    handler.setFormatter(UserFriendlyFormatter())
    handler.setLevel(stderr_level)

    handlers: list[logging.Handler] = [handler]
    root_level = stderr_level

    if log_to_file:
        file_handler = _build_file_handler(configured_level)
        if file_handler is not None:
            handlers.append(file_handler)
            # Levels are ordinals, so the lower number is the more verbose one.
            # The root logger has to pass through whatever the loudest handler wants.
            root_level = min(root_level, configured_level)

    # setup_logging() runs more than once per process: once at import, again
    # after the CLI args are parsed. Close the previous handlers so their file
    # descriptors are not leaked.
    root_logger = logging.getLogger()
    for old_handler in root_logger.handlers:
        old_handler.close()
    root_logger.setLevel(root_level)
    root_logger.handlers = handlers

    # Suppress verbose logs from dependencies
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module."""
    return logging.getLogger(name)
