from __future__ import annotations

import secrets
import time
from collections import defaultdict, deque
from threading import Lock

from flask import abort, request, session


CSRF_SESSION_KEY = "_csrf"
CSRF_COOKIE_NAME = "pick_csrf"
CSRF_COOKIE_MAX_AGE = 14 * 24 * 60 * 60


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
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def _safe_compare(expected, supplied) -> bool:
    if not expected or not supplied:
        return False
    try:
        return secrets.compare_digest(str(expected), str(supplied))
    except Exception:
        return False


def validate_csrf() -> None:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return

    supplied = (
        request.headers.get("X-CSRF-Token")
        or request.form.get("_csrf")
    )
    expected_session = session.get(CSRF_SESSION_KEY)
    expected_cookie = request.cookies.get(CSRF_COOKIE_NAME)

    session_ok = _safe_compare(expected_session, supplied)
    cookie_ok = _safe_compare(expected_cookie, supplied)

    if session_ok or cookie_ok:
        if supplied and not session_ok:
            session[CSRF_SESSION_KEY] = str(supplied)
        return

    abort(403, description="보안 토큰이 올바르지 않습니다.")


def attach_csrf_cookie(response):
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        return response

    current = request.cookies.get(CSRF_COOKIE_NAME)
    if _safe_compare(current, token):
        return response

    forwarded_proto = (
        request.headers.get("X-Forwarded-Proto", "")
        .split(",", 1)[0]
        .strip()
        .lower()
    )
    secure = bool(request.is_secure or forwarded_proto == "https")

    response.set_cookie(
        CSRF_COOKIE_NAME,
        str(token),
        max_age=CSRF_COOKIE_MAX_AGE,
        secure=secure,
        httponly=True,
        samesite="Lax",
        path="/",
    )
    return response


def client_key(prefix: str) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else request.remote_addr or "unknown"
    )
    return f"{prefix}:{ip}"
