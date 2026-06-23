"""Rate limits — in-memory locally, Redis (Upstash) in production."""

from __future__ import annotations

import threading
import time
from collections import defaultdict

from fastapi import HTTPException

from cloud.app.config import (
    GEN_COOLDOWN_SEC,
    GEN_HOURLY_LIMIT,
    IP_HOURLY_LIMIT,
)
from cloud.app import redis_store


class SlidingWindow:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_sec: float) -> bool:
        if redis_store.redis_available():
            return redis_store.sliding_allow(key, limit, window_sec)

        now = time.monotonic()
        cutoff = now - window_sec
        with self._lock:
            hits = [t for t in self._hits[key] if t > cutoff]
            if len(hits) >= limit:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True

    def seconds_until_allowed(self, key: str, limit: int, window_sec: float) -> float:
        if redis_store.redis_available():
            return redis_store.sliding_wait_sec(key, limit, window_sec)

        now = time.monotonic()
        cutoff = now - window_sec
        with self._lock:
            hits = sorted(t for t in self._hits[key] if t > cutoff)
        if len(hits) < limit:
            return 0.0
        return max(0.0, hits[0] + window_sec - now)


_ip_window = SlidingWindow()
_user_gen_window = SlidingWindow()
_user_cooldown = SlidingWindow()


def check_ip_limit(ip: str) -> None:
    if not ip:
        return
    if not _ip_window.allow(f"rl:ip:{ip}", IP_HOURLY_LIMIT, 3600.0):
        raise HTTPException(429, f"Too many requests from this IP (max {IP_HOURLY_LIMIT}/hour).")


def check_generate_limits(user_id: str) -> None:
    cooldown_key = f"rl:gen_cd:{user_id}"
    if not _user_cooldown.allow(cooldown_key, 1, float(GEN_COOLDOWN_SEC)):
        wait = int(_user_cooldown.seconds_until_allowed(cooldown_key, 1, float(GEN_COOLDOWN_SEC))) + 1
        raise HTTPException(429, f"Wait {wait}s before generating again.")

    hourly_key = f"rl:gen_hr:{user_id}"
    if not _user_gen_window.allow(hourly_key, GEN_HOURLY_LIMIT, 3600.0):
        raise HTTPException(429, f"Hourly generation limit reached ({GEN_HOURLY_LIMIT}/hour).")


def record_ip_hit(ip: str) -> None:
    if ip:
        _ip_window.allow(f"rl:ip:{ip}", IP_HOURLY_LIMIT, 3600.0)
