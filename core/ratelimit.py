"""
Fixed-window rate limiter — Redis-backed (multi-instance safe) with an in-memory
fallback when Redis is unavailable. Used to throttle auth endpoints (brute force).

Usage:
    ok, retry_after = await ratelimit.check("login:1.2.3.4", limit=10, window=300)
    if not ok: raise HTTPException(429, ...)
"""
from __future__ import annotations

import time

from .config import settings

try:
    from redis.asyncio import from_url as _redis_from_url
except Exception:  # redis not importable
    _redis_from_url = None

_redis = None
_mem: dict[str, tuple[int, float]] = {}  # key -> (count, window_reset_epoch)


_redis_unavailable = False


async def _get_redis():
    """Return a Redis client, or None if unavailable/misconfigured (caller then
    uses the in-memory fallback). A bad REDIS_URL must never raise here."""
    global _redis, _redis_unavailable
    if _redis_unavailable or _redis_from_url is None:
        return None
    url = (settings.redis_url or "").strip().strip('"').strip("'")
    if not url:
        return None
    if _redis is None:
        try:
            _redis = _redis_from_url(url, encoding="utf-8", decode_responses=True)
        except Exception:
            _redis_unavailable = True   # bad URL — stop retrying, use memory
            return None
    return _redis


async def check(key: str, limit: int, window: int) -> tuple[bool, int]:
    """Return (allowed, retry_after_seconds). Counts this hit against the window."""
    try:
        r = await _get_redis()
    except Exception:
        r = None
    if r is not None:
        try:
            rk = f"rl:{key}"
            n = await r.incr(rk)
            if n == 1:
                await r.expire(rk, window)
            if n > limit:
                ttl = await r.ttl(rk)
                return False, max(int(ttl), 1)
            return True, 0
        except Exception:
            pass  # fall through to in-memory

    now = time.time()
    count, reset = _mem.get(key, (0, now + window))
    if now > reset:
        count, reset = 0, now + window
    count += 1
    _mem[key] = (count, reset)
    if count > limit:
        return False, int(reset - now) + 1
    return True, 0
