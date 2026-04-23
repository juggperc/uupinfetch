"""
Circuit breaker pattern for external API calls.
Prevents cascading failures when a scraper is down or rate-limited.
"""

import time
import logging
from typing import Dict, Callable, Any, Optional
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """
    Circuit breaker for async functions.
    
    - CLOSED: Calls pass through normally.
    - OPEN: After failure_threshold failures within failure_window_seconds,
            calls fail immediately with fallback value.
    - HALF_OPEN: After recovery_timeout_seconds, one test call is allowed.
                   If it succeeds, state returns to CLOSED.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        failure_window_seconds: float = 60.0,
        recovery_timeout_seconds: float = 120.0,
        fallback_value: Any = None,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.failure_window_seconds = failure_window_seconds
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.fallback_value = fallback_value
        
        self.state = CircuitState.CLOSED
        self.failures: list[float] = []
        self.last_failure_time: Optional[float] = None
        self.half_open_test_started: Optional[float] = None
    
    def _record_failure(self):
        now = time.time()
        self.failures.append(now)
        self.last_failure_time = now
        # Prune old failures
        cutoff = now - self.failure_window_seconds
        self.failures = [f for f in self.failures if f > cutoff]
        
        if len(self.failures) >= self.failure_threshold:
            logger.warning(
                f"Circuit breaker '{self.name}' OPENED after {len(self.failures)} failures"
            )
            self.state = CircuitState.OPEN
    
    def _record_success(self):
        self.failures = []
        self.last_failure_time = None
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit breaker '{self.name}' CLOSED (recovery confirmed)")
        self.state = CircuitState.CLOSED
    
    def _should_attempt(self) -> bool:
        now = time.time()
        
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and (now - self.last_failure_time) > self.recovery_timeout_seconds:
                logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.half_open_test_started = now
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            # Only allow one test call
            if self.half_open_test_started and (now - self.half_open_test_started) < 30:
                return False
            self.half_open_test_started = now
            return True
        
        return True
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if not self._should_attempt():
            logger.debug(f"Circuit breaker '{self.name}' OPEN — returning fallback")
            return self.fallback_value
        
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            logger.warning(f"Circuit breaker '{self.name}' recorded failure: {e}")
            return self.fallback_value

# Registry of circuit breakers per external service
_breakers: Dict[str, CircuitBreaker] = {}

def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name=name, **kwargs)
    return _breakers[name]

def circuit_breaker(name: str, **kwargs):
    """Decorator for applying circuit breaker to async functions."""
    breaker = get_circuit_breaker(name, **kwargs)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator
