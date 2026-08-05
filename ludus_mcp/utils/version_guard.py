"""Server compatibility guard.

This release targets the Ludus 2.x API only. The guard no longer picks between
API shapes -- it confirms the server actually speaks v2 and turns a failure into
one clear message, instead of letting the tool fail somewhere less obvious.
"""

import inspect
from typing import Any

from ludus_mcp.exceptions import (
    LudusAPIError,
    LudusAuthenticationError,
    LudusConnectionError,
    LudusTimeoutError,
)


async def require_v2(client: Any, feature_name: str) -> dict[str, str] | None:
    """Confirm the server speaks the Ludus 2.x API.

    Returns None when the server is usable, or an error dict describing the
    problem. Verification happens once per client and is cached, so calling this
    from every tool costs a single request per session.

    Usage in tool functions:
        guard = await require_v2(client, "Blueprints")
        if guard:
            return guard
        # ... proceed
    """
    verify = getattr(client, "ensure_server_verified", None)
    if verify is None:
        return None

    try:
        result = verify()
        if inspect.isawaitable(result):
            await result
    except (LudusConnectionError, LudusTimeoutError) as e:
        return {
            "error": f"{feature_name} is unavailable: cannot reach the Ludus server.",
            "detail": str(e),
        }
    except LudusAuthenticationError as e:
        return {
            "error": f"{feature_name} is unavailable: authentication failed.",
            "detail": str(e),
        }
    except LudusAPIError as e:
        return {
            "error": (
                f"{feature_name} requires Ludus 2.0 or later, and this server "
                "does not serve the 2.x API."
            ),
            "detail": str(e),
        }

    return None
