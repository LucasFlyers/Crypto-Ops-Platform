"""
app/utils/retry.py
───────────────────
Retry decorators using tenacity.
Used primarily for AI API calls and external HTTP requests.
Provides exponential backoff with jitter to avoid thundering herd.
"""

import functools
from typing import Any, Callable, Sequence, Type

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random,
    before_sleep_log,
    RetryError,
)
import logging

from app.utils.logging import get_logger

logger = get_logger(__name__)


def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: Sequence[Type[Exception]] = (Exception,),
) -> Callable:
    """
    Decorator factory for sync functions with exponential backoff retry.

    Args:
        max_attempts: Maximum number of total attempts (including first try)
        min_wait: Minimum wait seconds between retries
        max_wait: Maximum wait seconds between retries
        exceptions: Tuple of exception types to retry on
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait)
            + wait_random(0, 1),
            retry=retry_if_exception_type(tuple(exceptions)),
            before_sleep=before_sleep_log(
                logging.getLogger(__name__), logging.WARNING
            ),
            reraise=True,
        )
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)
        return wrapper
    return decorator


def with_async_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: Sequence[Type[Exception]] = (Exception,),
) -> Callable:
    """
    Decorator factory for async functions with exponential backoff retry.
    Used for async AI API calls.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait)
            + wait_random(0, 1),
            retry=retry_if_exception_type(tuple(exceptions)),
            before_sleep=before_sleep_log(
                logging.getLogger(__name__), logging.WARNING
            ),
            reraise=True,
        )
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)
        return wrapper
    return decorator
