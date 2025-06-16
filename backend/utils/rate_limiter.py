"""Simple token bucket rate limiter."""
from __future__ import annotations

import threading
import time


class TokenBucket:
    """Token bucket limiter for API calls."""

    def __init__(self, rate: int, capacity: int | None = None) -> None:
        self.rate = rate
        self.capacity = capacity or rate
        self.tokens = self.capacity
        self.updated = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a token is available."""
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.updated
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate / 60)
            self.updated = now
            if self.tokens < 1:
                wait = (1 - self.tokens) * 60 / self.rate
                time.sleep(wait)
                self.updated = time.monotonic()
                self.tokens = 0
            self.tokens -= 1

