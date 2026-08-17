from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from statistics import median
from typing import Any

try:
    import ntplib
except Exception:
    ntplib = None

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None


NTP_SERVERS = [
    x.strip()
    for x in os.environ.get(
        "PICK_NTP_SERVERS",
        "time.google.com,time.cloudflare.com,pool.ntp.org,time.windows.com"
    ).split(",")
    if x.strip()
]

CACHE_SECONDS = max(30, int(os.environ.get("PICK_NTP_CACHE_SECONDS", "300")))
MAX_ACCEPTED_OFFSET = float(os.environ.get("PICK_NTP_MAX_OFFSET_SECONDS", "300"))
OUTLIER_TOLERANCE = float(os.environ.get("PICK_NTP_OUTLIER_SECONDS", "1.5"))
MIN_GOOD_SAMPLES = max(1, int(os.environ.get("PICK_NTP_MIN_SAMPLES", "2")))

_lock = threading.RLock()
_cached_offset = 0.0
_cached_at_monotonic = 0.0
_cached_source = "system"
_cached_samples: list[dict[str, Any]] = []
_anchor_utc = datetime.now(timezone.utc)
_anchor_mono = time.monotonic()
_last_sync_error = ""


@dataclass
class TimeStatus:
    source: str
    offset_seconds: float
    checked_at_utc: str
    samples: list[dict[str, Any]]
    accurate: bool
    confidence: str
    last_sync_error: str

    def to_dict(self):
        return asdict(self)


def _query_ntp(server: str, timeout: float = 2.0):
    if ntplib is None:
        raise RuntimeError("ntplib is not installed")

    client = ntplib.NTPClient()
    before = time.time()
    response = client.request(server, version=3, timeout=timeout)
    after = time.time()

    return {
        "server": server,
        "offset": float(response.offset),
        "delay": float(getattr(response, "delay", after - before)),
        "stratum": int(getattr(response, "stratum", 0) or 0),
    }


def _filter_samples(samples):
    if not samples:
        return []
    offsets = [s["offset"] for s in samples]
    center = median(offsets)
    good = [
        s for s in samples
        if abs(s["offset"] - center) <= OUTLIER_TOLERANCE
    ]
    return good or samples


def refresh_offset(force: bool = False) -> TimeStatus:
    global _cached_offset, _cached_at_monotonic, _cached_source
    global _cached_samples, _anchor_utc, _anchor_mono, _last_sync_error

    now_mono = time.monotonic()
    with _lock:
        if not force and (now_mono - _cached_at_monotonic) < CACHE_SECONDS:
            return status()

    raw_samples = []
    errors = []

    if ntplib is not None:
        for server in NTP_SERVERS:
            try:
                sample = _query_ntp(server)
                if abs(sample["offset"]) <= MAX_ACCEPTED_OFFSET:
                    raw_samples.append(sample)
                else:
                    errors.append(f"{server}: offset rejected")
            except Exception as exc:
                errors.append(f"{server}: {type(exc).__name__}")

    good = _filter_samples(raw_samples)

    with _lock:
        if len(good) >= MIN_GOOD_SAMPLES:
            offsets = [s["offset"] for s in good]
            _cached_offset = float(median(offsets))
            _cached_source = "ntp_consensus"
            _cached_samples = good
            _last_sync_error = "; ".join(errors[:4])
        elif good:
            _cached_offset = float(good[0]["offset"])
            _cached_source = "ntp_single"
            _cached_samples = good
            _last_sync_error = "; ".join(errors[:4])
        else:
            _cached_offset = 0.0
            _cached_source = "system"
            _cached_samples = []
            _last_sync_error = "; ".join(errors[:4]) or "NTP unavailable"

        # Anchor corrected UTC to monotonic time so later wall-clock jumps
        # do not cause event dates to jump unexpectedly.
        corrected = datetime.now(timezone.utc) + timedelta(seconds=_cached_offset)
        _anchor_utc = corrected
        _anchor_mono = time.monotonic()
        _cached_at_monotonic = _anchor_mono

    return status()


def status() -> TimeStatus:
    with _lock:
        source = _cached_source
        offset = _cached_offset
        samples = list(_cached_samples)
        err = _last_sync_error

    confidence = (
        "high" if source == "ntp_consensus"
        else "medium" if source == "ntp_single"
        else "fallback"
    )

    return TimeStatus(
        source=source,
        offset_seconds=round(offset, 6),
        checked_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        samples=samples,
        accurate=source.startswith("ntp"),
        confidence=confidence,
        last_sync_error=err,
    )


def utc_now() -> datetime:
    if (time.monotonic() - _cached_at_monotonic) >= CACHE_SECONDS:
        try:
            refresh_offset()
        except Exception:
            pass

    with _lock:
        elapsed = time.monotonic() - _anchor_mono
        return _anchor_utc + timedelta(seconds=elapsed)


def validate_timezone(name: str | None, fallback: str = "Asia/Seoul") -> str:
    if not name or ZoneInfo is None:
        return fallback
    value = str(name).strip()
    try:
        ZoneInfo(value)
        return value
    except Exception:
        return fallback


def now_in_timezone(name: str | None, fallback: str = "Asia/Seoul") -> datetime:
    tz_name = validate_timezone(name, fallback)
    if ZoneInfo is None:
        return utc_now()
    # DST is handled automatically by zoneinfo.
    return utc_now().astimezone(ZoneInfo(tz_name))


def seconds_until_next_local_midnight(name: str | None) -> int:
    local = now_in_timezone(name)
    tomorrow = (local + timedelta(days=1)).date()
    next_midnight = datetime(
        tomorrow.year, tomorrow.month, tomorrow.day,
        tzinfo=local.tzinfo
    )
    return max(0, int((next_midnight - local).total_seconds()))


try:
    refresh_offset(force=True)
except Exception:
    pass
