"""Response caching utilities.

This module provides caching functionality for read-only API operations
to improve performance and reduce load on the Ludus server.
"""

import asyncio
from functools import wraps
from datetime import datetime, timedelta
import hashlib
import json
from typing import Any, Callable, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AsyncLRUCache:
    """Async LRU cache with TTL (Time To Live).

    This implements a Least Recently Used cache with time-based expiration
    for async functions. It's useful for caching API responses that don't
    change frequently.

    Args:
        max_size: Maximum number of items to store in cache
        ttl_seconds: Time to live for cached items in seconds

    Example:
        cache = AsyncLRUCache(max_size=128, ttl_seconds=60)
        result = await cache.get_or_set(key, async_function, arg1, arg2)
    """

    def __init__(self, max_size: int = 128, ttl_seconds: int = 60):
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)
        self.cache: dict[str, tuple[Any, datetime]] = {}
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Create a cache key from function name and arguments.

        Args:
            func_name: Name of the function
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            MD5 hash of the serialized arguments
        """
        # Filter out 'self' and other non-hashable items
        filtered_kwargs = {
            k: v for k, v in kwargs.items() if k not in ("self", "cls")
        }

        key_data = {"func": func_name, "args": args, "kwargs": filtered_kwargs}

        try:
            key_str = json.dumps(key_data, sort_keys=True, default=str)
        except (TypeError, ValueError):
            # Fallback for non-serializable objects
            key_str = f"{func_name}:{str(args)}:{str(filtered_kwargs)}"

        return hashlib.md5(key_str.encode()).hexdigest()

    async def get_or_set(
        self, key: str, func: Callable, *args: Any, **kwargs: Any
    ) -> Any:
        """Get from cache or execute function and cache the result.

        Args:
            key: Cache key
            func: Async function to call if cache miss
            *args: Arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Cached or freshly computed result
        """
        async with self._lock:
            now = datetime.now()

            # Check if key exists and is not expired
            if key in self.cache:
                cached_value, cached_time = self.cache[key]

                if (now - cached_time) < self.ttl:
                    self._hits += 1
                    logger.debug(f"Cache hit for key: {key[:8]}...")
                    return cached_value
                else:
                    # Expired, remove it
                    del self.cache[key]
                    logger.debug(f"Cache expired for key: {key[:8]}...")

            self._misses += 1

        # Execute function (outside lock to allow concurrency)
        result = await func(*args, **kwargs)

        async with self._lock:
            # Cache the result
            self.cache[key] = (result, datetime.now())

            # Evict oldest entry if over size limit
            if len(self.cache) > self.max_size:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
                del self.cache[oldest_key]
                logger.debug(f"Cache evicted oldest key: {oldest_key[:8]}...")

        return result

    def invalidate(self, key: str | None = None) -> None:
        """Invalidate cache entries.

        Args:
            key: Specific key to invalidate, or None to clear all
        """
        if key is None:
            self.cache.clear()
            logger.info("Cache cleared")
        elif key in self.cache:
            del self.cache[key]
            logger.info(f"Cache invalidated for key: {key[:8]}...")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with hit rate, size, and other metrics
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "ttl_seconds": self.ttl.total_seconds(),
        }


# Global cache instance
_global_cache: AsyncLRUCache | None = None


def get_cache(max_size: int = 256, ttl_seconds: int = 30) -> AsyncLRUCache:
    """Get the global cache instance.

    Args:
        max_size: Maximum cache size (only used on first call)
        ttl_seconds: TTL in seconds (only used on first call)

    Returns:
        Global AsyncLRUCache instance
    """
    global _global_cache

    if _global_cache is None:
        _global_cache = AsyncLRUCache(max_size=max_size, ttl_seconds=ttl_seconds)

    return _global_cache


def cached(ttl_seconds: int = 30, max_size: int = 256):
    """Decorator to cache async function results.

    Args:
        ttl_seconds: Time to live for cached results
        max_size: Maximum number of cached results

    Returns:
        Decorator function

    Example:
        @cached(ttl_seconds=60)
        async def get_templates():
            return await api.get("/templates")
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache = get_cache(max_size=max_size, ttl_seconds=ttl_seconds)

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate cache key
            key = cache._make_key(func.__name__, args, kwargs)

            # Get or compute result
            return await cache.get_or_set(key, func, *args, **kwargs)

        # Add cache control methods to wrapper
        wrapper.cache_invalidate = lambda key=None: cache.invalidate(key)
        wrapper.cache_stats = cache.get_stats

        return wrapper

    return decorator
