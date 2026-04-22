"""
Shared HTTP utilities for scrapers: retry logic, rate limiting, and error handling.
"""

import functools
import asyncio
import time
import logging
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


def async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None,
):
    """
    Decorator for async functions that adds exponential backoff retry.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exceptions: Tuple of exceptions to catch and retry on
        on_retry: Optional callback(err, attempt) called on each retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt >= max_retries:
                        logger.warning(
                            f"{func.__name__} failed after {max_retries} attempts: {e}"
                        )
                        raise

                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    logger.info(
                        f"{func.__name__} attempt {attempt}/{max_retries} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    if on_retry:
                        try:
                            on_retry(e, attempt)
                        except Exception:
                            pass
                    await asyncio.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


class RateLimiter:
    """Simple per-host rate limiter."""

    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self._last_call = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_call
            if elapsed < self.min_interval:
                wait = self.min_interval - elapsed
                await asyncio.sleep(wait)
            self._last_call = time.time()


def http_error_message(status_code: int, source: str) -> str:
    """Return a user-friendly error message for HTTP status codes."""
    messages = {
        429: f"{source} rate limit exceeded. Please wait before retrying.",
        401: f"{source} authentication required. Please configure credentials.",
        403: f"{source} access denied. Check your API key or session tokens.",
        404: f"{source} endpoint not found. The API may have changed.",
        500: f"{source} server error. Please try again later.",
        502: f"{source} gateway error. Temporary outage likely.",
        503: f"{source} service unavailable. Temporary outage likely.",
    }
    return messages.get(status_code, f"{source} request failed with status {status_code}")
