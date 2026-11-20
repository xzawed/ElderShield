"""Simple in-process enroll rate limit (per client IP)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from app.core import config as config_module

_lock = threading.Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)


def allow_enroll(client_key: str) -> bool:
    """Return True if under per-minute cap for this client key."""
    limit = max(1, config_module.settings.enroll_rate_limit_per_minute)
    now = time.monotonic()
    window = 60.0
    with _lock:
        q = _hits[client_key]
        while q and (now - q[0]) > window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


def reset_for_tests() -> None:
    with _lock:
        _hits.clear()
