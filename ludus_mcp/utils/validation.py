"""Validation utilities."""

from typing import Any


def validate_range_name(name: str) -> str:
    """Validate and normalize a range name."""
    if not name or not name.strip():
        raise ValueError("Range name cannot be empty")
    # Remove invalid characters, keep alphanumeric, hyphens, underscores
    normalized = "".join(c for c in name if c.isalnum() or c in ("-", "_"))
    if not normalized:
        raise ValueError("Range name must contain at least one alphanumeric character")
    return normalized


def validate_host_name(name: str) -> str:
    """Validate and normalize a host name."""
    if not name or not name.strip():
        raise ValueError("Host name cannot be empty")
    normalized = "".join(c for c in name if c.isalnum() or c in ("-", "_", "."))
    if not normalized:
        raise ValueError("Host name must contain at least one alphanumeric character")
    return normalized


def validate_network_name(name: str) -> str:
    """Validate and normalize a network name."""
    if not name or not name.strip():
        raise ValueError("Network name cannot be empty")
    normalized = "".join(c for c in name if c.isalnum() or c in ("-", "_"))
    if not normalized:
        raise ValueError("Network name must contain at least one alphanumeric character")
    return normalized

