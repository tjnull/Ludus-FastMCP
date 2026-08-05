"""Tests for rate limiter."""

import pytest
import asyncio
from datetime import datetime, timedelta
from ludus_mcp.utils.rate_limit import RateLimiter, get_rate_limiter


class TestRateLimiter:
    """Test suite for RateLimiter class."""

    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self):
        """Test that requests under the limit are allowed immediately."""
        limiter = RateLimiter(max_requests=5, window_seconds=1)

        start_time = asyncio.get_event_loop().time()

        # Make 5 requests (under limit)
        for _ in range(5):
            await limiter.acquire()

        elapsed = asyncio.get_event_loop().time() - start_time

        # Should complete almost instantly (no waiting)
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self):
        """Test that requests over the limit are blocked."""
        limiter = RateLimiter(max_requests=3, window_seconds=1)

        start_time = asyncio.get_event_loop().time()

        # Make 3 requests (at limit)
        for _ in range(3):
            await limiter.acquire()

        # This should block until window expires
        await limiter.acquire()

        elapsed = asyncio.get_event_loop().time() - start_time

        # Should have waited approximately 1 second
        assert 0.9 <= elapsed <= 1.2

    @pytest.mark.asyncio
    async def test_sliding_window(self):
        """Test sliding window behavior."""
        limiter = RateLimiter(max_requests=2, window_seconds=0.5)

        # Make 2 requests
        await limiter.acquire()
        await limiter.acquire()

        # Wait half the window
        await asyncio.sleep(0.3)

        # Next request should still block
        start_time = asyncio.get_event_loop().time()
        await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start_time

        # Should have waited ~0.2s (remaining window time)
        assert 0.1 <= elapsed <= 0.4

    @pytest.mark.asyncio
    async def test_get_current_usage(self):
        """Test usage statistics."""
        limiter = RateLimiter(max_requests=10, window_seconds=1)

        # Make 3 requests
        for _ in range(3):
            await limiter.acquire()

        stats = limiter.get_current_usage()

        assert stats["current_requests"] == 3
        assert stats["max_requests"] == 10
        assert stats["window_seconds"] == 1.0
        assert stats["utilization_percent"] == 30.0

    @pytest.mark.asyncio
    async def test_reset(self):
        """Test reset functionality."""
        limiter = RateLimiter(max_requests=5, window_seconds=1)

        # Make some requests
        for _ in range(3):
            await limiter.acquire()

        assert limiter.get_current_usage()["current_requests"] == 3

        # Reset
        limiter.reset()

        assert limiter.get_current_usage()["current_requests"] == 0

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test rate limiter with concurrent requests."""
        limiter = RateLimiter(max_requests=5, window_seconds=1)

        async def make_request(request_id):
            await limiter.acquire()
            return request_id

        # Launch 10 concurrent requests
        tasks = [make_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All requests should complete
        assert len(results) == 10
        assert set(results) == set(range(10))

    @pytest.mark.asyncio
    async def test_over_limit_does_not_deadlock(self):
        """Waiting for a slot must not be done while holding the lock.

        acquire() used to recurse into itself inside `async with self._lock`;
        asyncio.Lock is not reentrant, so the retry blocked forever. Bounded by
        wait_for so a regression fails fast instead of hanging the suite.
        """
        limiter = RateLimiter(max_requests=1, window_seconds=0.2)

        await limiter.acquire()
        await asyncio.wait_for(limiter.acquire(), timeout=5)

        assert limiter.get_current_usage()["current_requests"] == 1

    @pytest.mark.asyncio
    async def test_lock_is_released_while_waiting(self):
        """A waiting caller must not stall unrelated callers on the same limiter."""
        limiter = RateLimiter(max_requests=1, window_seconds=0.3)
        await limiter.acquire()

        # This one has to wait for the window; usage stats take the same lock.
        waiter = asyncio.create_task(limiter.acquire())
        await asyncio.sleep(0.05)

        assert limiter.get_current_usage()["current_requests"] == 1
        await asyncio.wait_for(waiter, timeout=5)

    def test_get_rate_limiter_singleton(self):
        """Test that get_rate_limiter returns a singleton."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()

        # Should be the same instance
        assert limiter1 is limiter2
