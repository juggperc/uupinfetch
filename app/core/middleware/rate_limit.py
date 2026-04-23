"""
Rate limiting middleware for FastAPI.
Simple in-memory sliding window — sufficient for single-instance deployments.
Add Redis backend later for multi-node scaling.
"""

import time
import logging
from typing import Dict, Optional, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter per client IP."""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._windows: Dict[str, list] = {}
    
    def is_allowed(self, key: str) -> bool:
        now = time.time()
        window = self._windows.get(key, [])
        # Remove entries outside the window
        window = [t for t in window if now - t < self.window_seconds]
        if len(window) >= self.max_requests:
            self._windows[key] = window
            return False
        window.append(now)
        self._windows[key] = window
        return True
    
    def reset(self, key: str):
        self._windows.pop(key, None)

# Global limiter instance
_limiter = SlidingWindowRateLimiter(
    max_requests=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
    window_seconds=60
)

# Stricter limits for expensive endpoints
_search_limiter = SlidingWindowRateLimiter(max_requests=30, window_seconds=60)
_scan_limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware applying per-IP rate limits."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.enabled = settings.RATE_LIMIT_ENABLED
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)
        
        # Skip rate limiting for health checks and static assets
        path = request.url.path
        if path in ("/api/v1/health", "/api/docs", "/api/redoc", "/api/openapi.json"):
            return await call_next(request)
        if path.startswith("/static/"):
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        
        # Choose limiter based on endpoint cost
        if "/search" in path or "/compare" in path:
            limiter = _search_limiter
        elif "/trigger-scan" in path or "/scan" in path:
            limiter = _scan_limiter
        else:
            limiter = _limiter
        
        if not limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
            return Response(
                content='{"detail":"Rate limit exceeded. Please slow down."}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"}
            )
        
        return await call_next(request)
    
    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
