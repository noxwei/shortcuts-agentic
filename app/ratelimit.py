"""Sliding-window in-memory rate limiter."""

import time
from collections import defaultdict

from fastapi import Depends, HTTPException

from app.auth import verify_auth

_DEFAULT_MAX_REQUESTS = 60
_DEFAULT_WINDOW_SECONDS = 60


class RateLimiter:
    def __init__(self, max_requests: int = _DEFAULT_MAX_REQUESTS, window_seconds: int = _DEFAULT_WINDOW_SECONDS):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(now)
        return True


_limiter = RateLimiter()


async def require_rate_limit(user: str = Depends(verify_auth)) -> str:
    if not _limiter.check(user):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    return user
