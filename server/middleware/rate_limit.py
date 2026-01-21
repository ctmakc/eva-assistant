"""Simple rate limiting middleware for EVA API."""

import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger("eva.ratelimit")


class RateLimiter:
    """
    Simple in-memory rate limiter.
    Tracks requests per IP address with sliding window.
    """

    def __init__(
        self,
        requests_per_minute: int = 30,
        requests_per_hour: int = 500,
        burst_limit: int = 10
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit

        # Storage: {ip: [(timestamp, count), ...]}
        self._minute_window: Dict[str, list] = defaultdict(list)
        self._hour_window: Dict[str, list] = defaultdict(list)
        self._burst_window: Dict[str, list] = defaultdict(list)

    def _clean_old_entries(self, entries: list, window_seconds: int) -> list:
        """Remove entries older than the window."""
        cutoff = time.time() - window_seconds
        return [e for e in entries if e > cutoff]

    def is_allowed(self, ip: str) -> Tuple[bool, str]:
        """
        Check if request from IP is allowed.
        Returns (allowed, reason) tuple.
        """
        now = time.time()

        # Clean and check burst (last 1 second)
        self._burst_window[ip] = self._clean_old_entries(
            self._burst_window[ip], 1
        )
        if len(self._burst_window[ip]) >= self.burst_limit:
            return False, "burst"

        # Clean and check minute window
        self._minute_window[ip] = self._clean_old_entries(
            self._minute_window[ip], 60
        )
        if len(self._minute_window[ip]) >= self.requests_per_minute:
            return False, "minute"

        # Clean and check hour window
        self._hour_window[ip] = self._clean_old_entries(
            self._hour_window[ip], 3600
        )
        if len(self._hour_window[ip]) >= self.requests_per_hour:
            return False, "hour"

        # Record this request
        self._burst_window[ip].append(now)
        self._minute_window[ip].append(now)
        self._hour_window[ip].append(now)

        return True, ""

    def get_stats(self, ip: str) -> dict:
        """Get rate limit stats for an IP."""
        now = time.time()

        self._minute_window[ip] = self._clean_old_entries(
            self._minute_window[ip], 60
        )
        self._hour_window[ip] = self._clean_old_entries(
            self._hour_window[ip], 3600
        )

        return {
            "requests_last_minute": len(self._minute_window[ip]),
            "requests_last_hour": len(self._hour_window[ip]),
            "limit_per_minute": self.requests_per_minute,
            "limit_per_hour": self.requests_per_hour
        }


# Global rate limiter instance
_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    return _rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    Excludes certain paths from rate limiting.
    """

    # Paths to exclude from rate limiting
    EXCLUDED_PATHS = {
        "/api/v1/health",
        "/docs",
        "/openapi.json",
        "/",
        "/setup",
        "/login",
        "/logout",
        "/favicon.ico"
    }

    # Paths with higher limits (static files, audio)
    RELAXED_PATHS = {
        "/api/v1/audio/"
    }

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip rate limiting for excluded paths
        if path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Skip for relaxed paths (audio serving, etc.)
        for relaxed in self.RELAXED_PATHS:
            if path.startswith(relaxed):
                return await call_next(request)

        # Get client IP
        ip = self._get_client_ip(request)

        # Check rate limit
        limiter = get_rate_limiter()
        allowed, reason = limiter.is_allowed(ip)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {ip}: {reason}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Too many requests",
                    "reason": reason,
                    "retry_after": 60 if reason == "minute" else 3600
                }
            )

        response = await call_next(request)

        # Add rate limit headers
        stats = limiter.get_stats(ip)
        response.headers["X-RateLimit-Limit"] = str(stats["limit_per_minute"])
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, stats["limit_per_minute"] - stats["requests_last_minute"])
        )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP, considering proxies."""
        # Check X-Forwarded-For header (set by reverse proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # First IP in the list is the original client
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"
