"""Tests for file logging and the MCP request/response middleware.

Both originate from LouDeter's contribution in PR #8, with two changes made
before integrating:

* the file handler is guarded, because setup_logging() runs at import time and
  an unwritable home directory would otherwise stop the server from starting;
* the handler rotates, because the middleware writes a payload per request and
  response, which fills a file quickly on a long-running daemon.
"""

import logging
import logging.handlers
from unittest.mock import patch

import pytest

import ludus_mcp.utils.logging as log_module
from ludus_mcp.utils.logging import setup_logging


@pytest.fixture(autouse=True)
def restore_root_logger():
    """Keep the test run's own logging configuration intact."""
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    yield
    for h in root.handlers:
        if h not in saved_handlers:
            h.close()
    root.handlers, root.level = saved_handlers, saved_level


def _file_handlers(root=None):
    root = root or logging.getLogger()
    return [h for h in root.handlers if isinstance(h, logging.FileHandler)]


def test_unwritable_log_location_does_not_raise(tmp_path, capsys):
    """setup_logging() runs at import; a crash here means the server never starts."""
    blocked = tmp_path / "ro"
    blocked.mkdir(mode=0o500)

    with patch.object(log_module, "LOG_FILE", blocked / "sub" / "ludus.log"):
        setup_logging(quiet=True)  # must not raise

    assert not _file_handlers(), "file logging should be skipped, not fatal"
    assert logging.getLogger().handlers, "stderr logging must survive"
    assert "file logging disabled" in capsys.readouterr().err


def test_log_file_rotates(tmp_path):
    """DEBUG plus per-request payloads would otherwise grow without bound."""
    log_file = tmp_path / "ludus.log"
    with patch.object(log_module, "LOG_FILE", log_file), \
            patch.object(log_module, "LOG_FILE_MAX_BYTES", 2000), \
            patch.object(log_module, "LOG_FILE_BACKUP_COUNT", 2):
        setup_logging(quiet=True)
        logger = log_module.get_logger("spam")
        for _ in range(200):
            logger.warning("x" * 200)

        handlers = _file_handlers()
        assert handlers and isinstance(handlers[0], logging.handlers.RotatingFileHandler)

    written = sorted(p.name for p in tmp_path.iterdir())
    assert len(written) <= 3, f"rotation should cap the backups, got {written}"
    assert sum(p.stat().st_size for p in tmp_path.iterdir()) < 40_000


def test_quiet_silences_stderr_but_not_the_file(tmp_path):
    """An MCP client launches the server quietly; the file is the only record."""
    log_file = tmp_path / "ludus.log"
    settings = type("S", (), {"log_level": "DEBUG"})()

    with patch.object(log_module, "LOG_FILE", log_file), \
            patch.object(log_module, "get_settings", lambda: settings):
        setup_logging(quiet=True)

        root = logging.getLogger()
        stream = [
            h for h in root.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        ][0]
        file_handler = _file_handlers()[0]

        assert stream.level == logging.WARNING, "quiet must keep stderr clean"
        assert file_handler.level == logging.DEBUG, "the file keeps the detail"
        # The root must pass DEBUG through, or the file handler never sees it.
        assert root.level == logging.DEBUG

        log_module.get_logger("t").debug("recorded")

    assert "recorded" in log_file.read_text()


def test_daemon_mode_skips_the_file_handler(tmp_path):
    """The daemon dup2()s stderr into the same file; a handler would double it."""
    with patch.object(log_module, "LOG_FILE", tmp_path / "ludus.log"):
        setup_logging(quiet=False, log_to_file=False)

    assert not _file_handlers()


def test_repeated_setup_does_not_leak_handlers(tmp_path):
    """setup_logging() runs once at import and again after argv is parsed."""
    with patch.object(log_module, "LOG_FILE", tmp_path / "ludus.log"):
        setup_logging(quiet=True)
        first = _file_handlers()[0]
        setup_logging(quiet=False)

        assert len(_file_handlers()) == 1, "the previous handler must be replaced"
        assert first.stream is None or first.stream.closed, "old file handle must be closed"


# ---------- middleware ----------

@pytest.mark.asyncio
async def test_middleware_logs_both_directions(caplog):
    from ludus_mcp.server.mcp_logging_middleware import RequestResponseLoggingMiddleware

    class Ctx:
        method = "tools/call"
        type = "request"
        message = {"name": "get_range", "arguments": {}}

    async def call_next(_ctx):
        return {"result": "ok"}

    with caplog.at_level(logging.DEBUG, logger="ludus_mcp.mcp_requests"):
        result = await RequestResponseLoggingMiddleware().on_message(Ctx(), call_next)

    assert result == {"result": "ok"}
    text = caplog.text
    assert "--> request tools/call" in text and "get_range" in text
    assert "<-- request tools/call" in text and "ok" in text


@pytest.mark.asyncio
async def test_middleware_logs_and_reraises_errors(caplog):
    from ludus_mcp.server.mcp_logging_middleware import RequestResponseLoggingMiddleware

    class Ctx:
        method = "tools/call"
        type = "request"
        message = {"name": "boom"}

    async def call_next(_ctx):
        raise RuntimeError("kaboom")

    with caplog.at_level(logging.DEBUG, logger="ludus_mcp.mcp_requests"):
        with pytest.raises(RuntimeError, match="kaboom"):
            await RequestResponseLoggingMiddleware().on_message(Ctx(), call_next)

    assert "error after" in caplog.text and "kaboom" in caplog.text


@pytest.mark.asyncio
async def test_middleware_truncates_large_payloads(caplog):
    """A single 400KB deployment log must not be written to the file in full."""
    from ludus_mcp.server.mcp_logging_middleware import (
        MAX_PAYLOAD_LENGTH,
        RequestResponseLoggingMiddleware,
    )

    class Ctx:
        method = "tools/call"
        type = "request"
        message = {"name": "get_range_logs"}

    async def call_next(_ctx):
        return {"result": "y" * 100_000}

    with caplog.at_level(logging.DEBUG, logger="ludus_mcp.mcp_requests"):
        await RequestResponseLoggingMiddleware().on_message(Ctx(), call_next)

    assert "...(truncated)" in caplog.text
    assert len(caplog.text) < MAX_PAYLOAD_LENGTH * 3
