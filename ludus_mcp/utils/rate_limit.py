"""Rate limiting utilities.

This module provides rate limiting functionality to prevent overwhelming
the Ludus API with too many requests.
"""

import asyncio
from collections import deque
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for async operations.

    This implements a sliding window rate limiter that tracks requests
    over a time window and enforces a maximum request rate.

    Args:
        max_requests: Maximum number of requests allowed in the time window
        window_seconds: Time window in seconds

    Example:
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        await limiter.acquire()  # Wait if needed, then proceed
        # ... make API request
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self.requests: deque[datetime] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire permission to make a request.

        This will block if the rate limit has been exceeded, waiting
        until a request slot becomes available.
        """
        async with self._lock:
            now = datetime.now()

            # Remove requests outside the time window
            while self.requests and (now - self.requests[0]) > self.window:
                self.requests.popleft()

            # If at limit, calculate sleep time
            if len(self.requests) >= self.max_requests:
                # Sleep until the oldest request expires
                oldest_request = self.requests[0]
                sleep_until = oldest_request + self.window
                sleep_time = (sleep_until - now).total_seconds()

                if sleep_time > 0:
                    logger.debug(
                        f"Rate limit reached ({len(self.requests)}/{self.max_requests}). "
                        f"Waiting {sleep_time:.1f}s..."
                    )
                    await asyncio.sleep(sleep_time)

                # Recursive call after sleeping
                return await self.acquire()

            # Record this request
            self.requests.append(now)

    def get_current_usage(self) -> dict[str, any]:
        """Get current rate limiter statistics.

        Returns:
            Dictionary with current request count and limit info
        """
        now = datetime.now()

        # Clean old requests
        while self.requests and (now - self.requests[0]) > self.window:
            self.requests.popleft()

        return {
            "current_requests": len(self.requests),
            "max_requests": self.max_requests,
            "window_seconds": self.window.total_seconds(),
            "utilization_percent": (len(self.requests) / self.max_requests) * 100,
        }

    def reset(self) -> None:
        """Reset the rate limiter, clearing all tracked requests."""
        self.requests.clear()


# Global rate limiter instance (can be configured via settings)
_global_rate_limiter: RateLimiter | None = None


def get_rate_limiter(
    max_requests: int = 100, window_seconds: int = 60
) -> RateLimiter:
    """Get the global rate limiter instance.

    Args:
        max_requests: Maximum requests per window (only used on first call)
        window_seconds: Window size in seconds (only used on first call)

    Returns:
        Global RateLimiter instance
    """
    global _global_rate_limiter

    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter(
            max_requests=max_requests, window_seconds=window_seconds
        )

    return _global_rate_limiter
