"""Upstash Redis — distributed rate limits + LLM queue slots."""

from __future__ import annotations

import logging
import time
from typing import Any

from cloud.app.config import REDIS_URL

logger = logging.getLogger("plg.redis")

_client: Any = None
_checked = False


def redis_client() -> Any | None:
    global _client, _checked
    if _checked:
        return _client
    _checked = True
    if not REDIS_URL:
        return None
    try:
        import redis

        _client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2.0)
        _client.ping()
        logger.info("Redis connected (Upstash)")
        return _client
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis unavailable, using in-memory fallback: %s", exc)
        _client = None
        return None


def redis_available() -> bool:
    return redis_client() is not None


def sliding_allow(key: str, limit: int, window_sec: float) -> bool:
    """Return True if request is allowed under sliding window limit."""
    client = redis_client()
    if not client:
        return True  # caller uses in-memory fallback

    now = time.time()
    pipe = client.pipeline()
    pipe.zremrangebyscore(key, 0, now - window_sec)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, int(window_sec) + 10)
    _, _, count, _ = pipe.execute()
    if count > limit:
        client.zrem(key, str(now))
        return False
    return True


def sliding_wait_sec(key: str, limit: int, window_sec: float) -> float:
    client = redis_client()
    if not client:
        return 0.0
    now = time.time()
    oldest = client.zrange(key, 0, 0, withscores=True)
    if not oldest or len(client.zrange(key, 0, -1)) < limit:
        return 0.0
    return max(0.0, oldest[0][1] + window_sec - now)


def incr_slot(key: str, max_slots: int, ttl_sec: int = 300) -> bool:
    """Acquire distributed slot. Return False if at capacity."""
    client = redis_client()
    if not client:
        return True
    count = int(client.incr(key))
    if count == 1:
        client.expire(key, ttl_sec)
    if count > max_slots:
        client.decr(key)
        return False
    return True


def decr_slot(key: str) -> None:
    client = redis_client()
    if not client:
        return
    try:
        val = int(client.decr(key))
        if val < 0:
            client.set(key, 0)
    except Exception:  # noqa: BLE001
        pass
