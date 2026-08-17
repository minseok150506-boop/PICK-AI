from __future__ import annotations

import secrets
import time
from collections import defaultdict, deque
from threading import Lock

from flask import abort, request, session


class SlidingWindowLimiter:
    def __init__(self):
        self._events = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._events[key]
            cutoff = now - window_seconds
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


limiter = SlidingWindowLimiter()


def csrf_token() -> str:
    token = session.get("_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf"] = token
    return token


def validate_csrf() -> None:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    expected = session.get("_csrf")
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("_csrf")
    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        abort(403, description="보안 토큰이 올바르지 않습니다.")


def client_key(prefix: str) -> str:
    # Reverse proxy may pass X-Forwarded-For. Trust only the first value as a
    # rate-limit hint; it is not used for authentication.
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",")[0].strip() if forwarded else request.remote_addr or "unknown"
    return f"{prefix}:{ip}"
