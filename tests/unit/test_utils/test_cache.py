"""Tests for caching utility."""

import pytest
import asyncio
from ludus_mcp.utils.cache import AsyncLRUCache, cached, get_cache


class TestAsyncLRUCache:
    """Test suite for AsyncLRUCache class."""

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache hit returns cached value."""
        cache = AsyncLRUCache(max_size=10, ttl_seconds=60)
        call_count = 0

        async def expensive_function():
            nonlocal call_count
            call_count += 1
            return "result"

        # First call - cache miss
        result1 = await cache.get_or_set("key1", expensive_function)
        assert result1 == "result"
        assert call_count == 1

        # Second call - cache hit
        result2 = await cache.get_or_set("key1", expensive_function)
        assert result2 == "result"
        assert call_count == 1  # Function not called again

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss calls function."""
        cache = AsyncLRUCache(max_size=10, ttl_seconds=60)
        call_count = 0

        async def expensive_function():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        result1 = await cache.get_or_set("key1", expensive_function)
        result2 = await cache.get_or_set("key2", expensive_function)

        assert result1 == "result_1"
        assert result2 == "result_2"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        cache = AsyncLRUCache(max_size=10, ttl_seconds=0.1)
        call_count = 0

        async def expensive_function():
            nonlocal call_count
            call_count += 1
            return "result"

        # First call
        result1 = await cache.get_or_set("key1", expensive_function)
        assert call_count == 1

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Should be expired and call function again
        result2 = await cache.get_or_set("key1", expensive_function)
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test that LRU eviction works correctly."""
        cache = AsyncLRUCache(max_size=3, ttl_seconds=60)

        async def make_value(key):
            return f"value_{key}"

        # Fill cache to max
        await cache.get_or_set("key1", make_value, "key1")
        await cache.get_or_set("key2", make_value, "key2")
        await cache.get_or_set("key3", make_value, "key3")

        assert cache.get_stats()["size"] == 3

        # Add one more - should evict oldest
        await cache.get_or_set("key4", make_value, "key4")

        assert cache.get_stats()["size"] == 3

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = AsyncLRUCache(max_size=10, ttl_seconds=60)

        async def expensive_function():
            return "result"

        # Add to cache
        await cache.get_or_set("key1", expensive_function)
        assert cache.get_stats()["size"] == 1

        # Invalidate specific key
        cache.invalidate("key1")
        assert cache.get_stats()["size"] == 0

        # Add multiple entries
        await cache.get_or_set("key1", expensive_function)
        await cache.get_or_set("key2", expensive_function)

        # Invalidate all
        cache.invalidate()
        assert cache.get_stats()["size"] == 0

    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics."""
        cache = AsyncLRUCache(max_size=10, ttl_seconds=60)

        async def func():
            return "result"

        # Initial stats
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total_requests"] == 0

        # Cache miss
        await cache.get_or_set("key1", func)
        stats = cache.get_stats()
        assert stats["misses"] == 1

        # Cache hit
        await cache.get_or_set("key1", func)
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["hit_rate_percent"] == 50.0

    @pytest.mark.asyncio
    async def test_cached_decorator(self):
        """Test @cached decorator."""
        call_count = 0

        @cached(ttl_seconds=60)
        async def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y

        # First call
        result1 = await expensive_function(1, 2)
        assert result1 == 3
        assert call_count == 1

        # Second call with same args - should hit cache
        result2 = await expensive_function(1, 2)
        assert result2 == 3
        assert call_count == 1

        # Call with different args - cache miss
        result3 = await expensive_function(2, 3)
        assert result3 == 5
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cached_decorator_with_kwargs(self):
        """Test @cached decorator with keyword arguments."""
        call_count = 0

        @cached(ttl_seconds=60)
        async def function_with_kwargs(a, b, c=10):
            nonlocal call_count
            call_count += 1
            return a + b + c

        # Call with kwargs
        result1 = await function_with_kwargs(1, 2, c=3)
        assert result1 == 6
        assert call_count == 1

        # Same call - cache hit
        result2 = await function_with_kwargs(1, 2, c=3)
        assert result2 == 6
        assert call_count == 1

        # Different kwargs - cache miss
        result3 = await function_with_kwargs(1, 2, c=5)
        assert result3 == 8
        assert call_count == 2

    def test_get_cache_singleton(self):
        """Test that get_cache returns a singleton."""
        cache1 = get_cache()
        cache2 = get_cache()

        # Should be the same instance
        assert cache1 is cache2


class TestCacheEvictionAndIsolation:
    """Regression tests for LRU ordering and per-decorator cache isolation."""

    @pytest.mark.asyncio
    async def test_eviction_drops_least_recently_used_not_oldest_inserted(self):
        """A key that keeps being read must survive eviction.

        Eviction used to pick the oldest *insertion*, so a hot key was thrown
        out while a newer but untouched key stayed.
        """
        cache = AsyncLRUCache(max_size=2, ttl_seconds=60)

        async def value(v):
            return v

        await cache.get_or_set("hot", value, "hot")
        await cache.get_or_set("cold", value, "cold")

        # Touch "hot" so it is the most recently used entry
        assert await cache.get_or_set("hot", value, "ignored") == "hot"

        # Inserting a third entry must evict "cold", the least recently used
        await cache.get_or_set("new", value, "new")

        assert cache.get_stats()["size"] == 2
        assert "hot" in cache.cache
        assert "cold" not in cache.cache

    @pytest.mark.asyncio
    async def test_cache_hit_does_not_extend_ttl(self):
        """Reads must not keep a stale entry alive forever."""
        cache = AsyncLRUCache(max_size=10, ttl_seconds=0.2)
        calls = 0

        async def counter():
            nonlocal calls
            calls += 1
            return calls

        await cache.get_or_set("k", counter)
        await asyncio.sleep(0.1)
        await cache.get_or_set("k", counter)  # hit, must not reset the clock
        await asyncio.sleep(0.15)
        await cache.get_or_set("k", counter)  # entry is now past its TTL

        assert calls == 2

    @pytest.mark.asyncio
    async def test_each_decorated_function_honors_its_own_ttl(self):
        """@cached(...) arguments must not be ignored in favour of a shared cache."""
        get_cache()  # ensure the global instance exists first

        @cached(ttl_seconds=0.1, max_size=8)
        async def short_lived():
            return object()

        @cached(ttl_seconds=60, max_size=8)
        async def long_lived():
            return object()

        first_short, first_long = await short_lived(), await long_lived()
        await asyncio.sleep(0.15)

        assert await short_lived() is not first_short  # expired
        assert await long_lived() is first_long  # still cached

    @pytest.mark.asyncio
    async def test_decorated_functions_do_not_share_entries(self):
        @cached(ttl_seconds=60)
        async def alpha():
            return "alpha"

        @cached(ttl_seconds=60)
        async def beta():
            return "beta"

        assert await alpha() == "alpha"
        assert await beta() == "beta"
        assert alpha.cache_stats()["size"] == 1
        assert beta.cache_stats()["size"] == 1
