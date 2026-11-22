"""Best-effort, single-process abuse and cost guards for the public demo.

For horizontal scaling use a shared Redis limiter and provider billing caps.
"""
from __future__ import annotations
from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import BoundedSemaphore, Lock
from time import monotonic


class DemoLimiter:
    def __init__(self, per_minute: int = 5, per_day: int = 75, parallel: int = 2):
        self.per_minute = max(1, per_minute)
        self.per_day = max(1, per_day)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._day = datetime.now(timezone.utc).date()
        self._daily_count = 0
        self._lock = Lock()
        self._slots = BoundedSemaphore(value=max(1, parallel))

    def reserve(self, ip: str) -> str | None:
        """Returns a rejection reason or None. Consumes quota on accepted requests."""
        now = monotonic()
        today = datetime.now(timezone.utc).date()
        with self._lock:
            if today != self._day:
                self._day, self._daily_count = today, 0
                self._hits.clear()
            recent = self._hits[ip]
            while recent and now - recent[0] >= 60:
                recent.popleft()
            if len(recent) >= self.per_minute:
                return "Per-client request rate exceeded"
            if self._daily_count >= self.per_day:
                return "Demo daily analysis budget exhausted"
            if not self._slots.acquire(blocking=False):
                return "Too many concurrent analyses"
            recent.append(now)
            self._daily_count += 1
            return None

    def release(self) -> None:
        self._slots.release()
