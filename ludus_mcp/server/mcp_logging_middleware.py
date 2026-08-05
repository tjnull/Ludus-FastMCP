"""FastMCP middleware that logs every request and response at DEBUG level.

Originally contributed by LouDeter (https://github.com/tjnull/Ludus-FastMCP/pull/8).

When an AI assistant drives this server, the interesting failures are in what it
actually sent, not in what the API returned. This records both directions with
timing, so a confusing tool result can be traced back to the arguments that
produced it.

Enabled automatically when LOG_LEVEL=DEBUG; see setup_logging().
"""

import logging
import time
from typing import Any

import pydantic_core
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext

logger = logging.getLogger("ludus_mcp.mcp_requests")

MAX_PAYLOAD_LENGTH = 2000


def _serialize(value: Any) -> str:
    """Render a payload for the log, truncated so one call cannot flood the file."""
    payload = pydantic_core.to_json(value, fallback=str).decode()
    if len(payload) > MAX_PAYLOAD_LENGTH:
        return payload[:MAX_PAYLOAD_LENGTH] + "...(truncated)"
    return payload


class RequestResponseLoggingMiddleware(Middleware):
    """Logs the payload of every incoming MCP message and its outgoing result/error."""

    async def on_message(
        self, context: MiddlewareContext[Any], call_next: CallNext[Any, Any]
    ) -> Any:
        method = context.method or "unknown"
        logger.debug(f"--> {context.type} {method}: {_serialize(context.message)}")

        start = time.perf_counter()
        try:
            result = await call_next(context)
        except Exception as e:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.debug(f"<-- {context.type} {method} error after {duration_ms}ms: {e}")
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.debug(f"<-- {context.type} {method} ({duration_ms}ms): {_serialize(result)}")
        return result
