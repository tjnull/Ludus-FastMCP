"""Version guard utility for v2-only tools."""

from typing import Any


def require_v2(client: Any, feature_name: str) -> dict[str, str] | None:
    """Check if client is v2. Returns error dict if v1, None if v2.

    Usage in tool functions:
        guard = require_v2(client, "Blueprints")
        if guard:
            return guard
        # ... proceed with v2 logic
    """
    if getattr(client, "api_version", "v1") != "v2":
        return {
            "error": f"{feature_name} requires Ludus 2.0 or later. "
            f"Your server is running {getattr(client, 'api_version', 'v1')}."
        }
    return None
