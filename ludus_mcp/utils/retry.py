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
    """Context manager for retry operations with more control.

    This provides an alternative to the decorator when you need
    more fine-grained control over retry logic.

    Example:
        retry = RetryContext(max_attempts=3)
        async with retry:
            result = await some_operation()
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

    async def __aenter__(self):
        """Enter retry context."""
        self.attempt += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit retry context and handle retries."""
        if exc_type is None:
            return True

        if not issubclass(exc_type, self.exceptions):
            return False

        self.last_exception = exc_val

        if self.attempt >= self.max_attempts:
            logger.error(
                f"Operation failed after {self.max_attempts} attempts: {exc_val}"
            )
            return False

        delay = min(
            self.initial_delay * (self.backoff_factor ** (self.attempt - 1)),
            self.max_delay,
        )

        logger.warning(
            f"Attempt {self.attempt}/{self.max_attempts} failed: "
            f"{exc_type.__name__}: {exc_val}. Retrying in {delay:.1f}s..."
        )

        await asyncio.sleep(delay)
        return True
