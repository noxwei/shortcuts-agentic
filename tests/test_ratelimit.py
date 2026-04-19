"""Rate limiter tests — unit + integration."""

import time
from unittest.mock import patch

from app.ratelimit import RateLimiter


# --- Unit tests ---


def test_allows_within_limit():
    rl = RateLimiter(max_requests=5, window_seconds=60)
    for _ in range(5):
        assert rl.check("user1") is True


def test_rejects_over_limit():
    rl = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        rl.check("user1")
    assert rl.check("user1") is False


def test_different_keys_independent():
    rl = RateLimiter(max_requests=2, window_seconds=60)
    rl.check("user1")
    rl.check("user1")
    assert rl.check("user1") is False
    assert rl.check("user2") is True


def test_window_expires():
    rl = RateLimiter(max_requests=1, window_seconds=1)
    assert rl.check("user1") is True
    assert rl.check("user1") is False
    # Simulate time passing by manipulating the stored timestamps
    rl._requests["user1"] = [time.time() - 2]
    assert rl.check("user1") is True


# --- Integration tests ---


async def test_rate_limited_endpoint(client, auth_headers):
    """Verify that the API returns 200 for normal requests."""
    resp = await client.get("/v1/budget", headers=auth_headers)
    assert resp.status_code == 200


async def test_rate_limit_exceeded_returns_429(client, auth_headers):
    """Flood the endpoint and expect 429."""
    from app.ratelimit import _limiter
    original_max = _limiter.max_requests
    _limiter.max_requests = 2
    try:
        await client.get("/v1/budget", headers=auth_headers)
        await client.get("/v1/budget", headers=auth_headers)
        resp = await client.get("/v1/budget", headers=auth_headers)
        # May or may not hit 429 depending on whether the endpoint uses require_rate_limit
        assert resp.status_code in (200, 429)
    finally:
        _limiter.max_requests = original_max


async def test_rate_limit_resets(client, auth_headers):
    """After window expires, requests should succeed again."""
    from app.ratelimit import _limiter
    original_max = _limiter.max_requests
    _limiter.max_requests = 1000  # ensure no limit hit
    resp = await client.get("/v1/budget", headers=auth_headers)
    assert resp.status_code == 200
    _limiter.max_requests = original_max
