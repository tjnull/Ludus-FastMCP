"""Retry utilities with exponential backoff.

This module provides decorators and utilities for retrying failed operations
with configurable backoff strategies.
"""

import asyncio
from functools import wraps
from typing import TypeVar, Callable, Any
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


def async_retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """Decorator for async functions with exponential backoff retry.

    Args:
        max_attempts: Maximum number of attempts (including initial)
        backoff_factor: Multiplier for exponential backoff
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated function with retry logic

    Example:
        @async_retry(max_attempts=3, exceptions=(ConnectionError,))
        async def fetch_data():
            return await api.get("/data")
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    # If this was the last attempt, re-raise
                    if attempt == max_attempts - 1:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(initial_delay * (backoff_factor**attempt), max_delay)

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}): "
                        f"{type(e).__name__}: {e}. Retrying in {delay:.1f}s..."
                    )

                    await asyncio.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


class RetryContext:
    """Retry helper for code that cannot use the @async_retry decorator.

    A context manager cannot re-run its own body, so this is used as an async
    iterator that yields one attempt at a time:

        async for attempt in RetryContext(max_attempts=3, exceptions=(IOError,)):
            with attempt:
                result = await some_operation()

    Each `with attempt:` block swallows a retryable error and schedules another
    pass; the final failure propagates.

    The previous `async with retry:` form was unusable and dangerous: __aexit__
    returned True on failure, which SUPPRESSED the exception without re-running
    anything, so a failed operation looked like a successful one.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exceptions: tuple[type[Exception], ...] = (Exception,),
    ):
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exceptions = exceptions
        self.attempt = 0
        self.last_exception: Exception | None = None
        self._succeeded = False

    def __aiter__(self):
        self.attempt = 0
        self._succeeded = False
        return self

    async def __anext__(self) -> "_RetryAttempt":
        if self._succeeded or self.attempt >= self.max_attempts:
            raise StopAsyncIteration

        if self.attempt:  # back off before every attempt after the first
            delay = min(
                self.initial_delay * (self.backoff_factor ** (self.attempt - 1)),
                self.max_delay,
            )
            logger.warning(
                f"Attempt {self.attempt}/{self.max_attempts} failed: "
                f"{self.last_exception}. Retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)

        self.attempt += 1
        return _RetryAttempt(self)

    async def __aenter__(self):
        raise TypeError(
            "RetryContext cannot be used with 'async with' - a context manager "
            "cannot re-run its own body, so failures were silently swallowed. "
            "Use: async for attempt in RetryContext(...): with attempt: ..."
        )

    async def __aexit__(self, exc_type, exc_val, exc_tb):  # pragma: no cover
        return False


class _RetryAttempt:
    """One attempt handed out by RetryContext; swallows retryable failures."""

    def __init__(self, ctx: "RetryContext") -> None:
        self._ctx = ctx

    def __enter__(self) -> "_RetryAttempt":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            self._ctx._succeeded = True
            return False
        if not issubclass(exc_type, self._ctx.exceptions):
            return False
        self._ctx.last_exception = exc_val
        if self._ctx.attempt >= self._ctx.max_attempts:
            logger.error(
                f"Operation failed after {self._ctx.max_attempts} attempts: {exc_val}"
            )
            return False  # out of attempts: let the real error propagate
        return True  # retryable and attempts remain: loop again
