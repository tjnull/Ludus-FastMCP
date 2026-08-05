"""Tests for RetryContext.

The old `async with retry:` form returned True from __aexit__ on failure, which
suppressed the exception without re-running anything - a failed operation was
indistinguishable from a successful one.
"""

import asyncio

import pytest

from ludus_mcp.utils.retry import RetryContext


@pytest.mark.asyncio
async def test_retries_until_success():
    calls = 0
    async for attempt in RetryContext(max_attempts=4, initial_delay=0, exceptions=(ValueError,)):
        with attempt:
            calls += 1
            if calls < 3:
                raise ValueError("not yet")
    assert calls == 3


@pytest.mark.asyncio
async def test_final_failure_propagates():
    calls = 0
    with pytest.raises(ValueError, match="always"):
        async for attempt in RetryContext(max_attempts=3, initial_delay=0, exceptions=(ValueError,)):
            with attempt:
                calls += 1
                raise ValueError("always")
    assert calls == 3, "should exhaust every attempt before raising"


@pytest.mark.asyncio
async def test_non_retryable_exception_propagates_immediately():
    calls = 0
    with pytest.raises(KeyError):
        async for attempt in RetryContext(max_attempts=5, initial_delay=0, exceptions=(ValueError,)):
            with attempt:
                calls += 1
                raise KeyError("nope")
    assert calls == 1


@pytest.mark.asyncio
async def test_success_on_first_try_runs_once():
    calls = 0
    async for attempt in RetryContext(max_attempts=3, initial_delay=0):
        with attempt:
            calls += 1
    assert calls == 1


@pytest.mark.asyncio
async def test_async_with_is_refused_rather_than_swallowing_errors():
    """The old usage silently hid failures; it must now fail loudly."""
    with pytest.raises(TypeError, match="cannot be used with 'async with'"):
        async with RetryContext(max_attempts=2):
            pass
