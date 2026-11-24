"""Thread-safe, in-memory failed-login limiter for a single worker."""

import threading
import secrets
import time
from collections import OrderedDict


class FailedLoginLimiter:
    def __init__(self, max_attempts=5, window_seconds=900, max_clients=10000):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.max_clients = max_clients
        self._attempts = OrderedDict()
        self._lock = threading.Lock()
        self._inflight = {}

    def _cleanup(self, now):
        for key in list(self._attempts):
            timestamps = [
                t for t in self._attempts[key]
                if now - t < self.window_seconds
            ]
            if timestamps:
                self._attempts[key] = timestamps
            else:
                self._attempts.pop(key, None)

        for key in list(self._inflight):
            pending = {
                token: started
                for token, started in self._inflight[key].items()
                if now - started < self.window_seconds
            }

            if pending:
                self._inflight[key] = pending
            else:
                self._inflight.pop(key, None)

    def is_blocked(self, key):
        now = time.monotonic()
        with self._lock:
            self._cleanup(now)
            timestamps = self._attempts.get(key, [])
            return len(timestamps) >= self.max_attempts

    def record_failure(self, key):
        now = time.monotonic()
        with self._lock:
            self._cleanup(now)

            timestamps = [
                t for t in self._attempts.get(key, [])
                if now - t < self.window_seconds
            ]

            if len(timestamps) < self.max_attempts:
                timestamps.append(now)

            self._attempts[key] = timestamps
            self._attempts.move_to_end(key)

            while len(self._attempts) > self.max_clients:
                self._attempts.popitem(last=False)

    def clear(self, key):
        with self._lock:
            self._attempts.pop(key, None)

    def allow_attempt(self, key):
        """Atomically check and reserve one login attempt."""
        now = time.monotonic()

        with self._lock:
            self._cleanup(now)

            timestamps = self._attempts.get(key, [])

            if len(timestamps) >= self.max_attempts:
                return False

            timestamps.append(now)
            self._attempts[key] = timestamps
            self._attempts.move_to_end(key)

            while len(self._attempts) > self.max_clients:
                self._attempts.popitem(last=False)

            return True


    def reserve_attempt(self, key):
        """Atomically reserve a uniquely identified login attempt."""
        now = time.monotonic()

        with self._lock:
            self._cleanup(now)
            timestamps = self._attempts.get(key, [])
            pending = self._inflight.get(key, {})

            if len(timestamps) + len(pending) >= self.max_attempts:
                return None

            known_clients = set(self._attempts) | set(self._inflight)

            if key not in known_clients and len(known_clients) >= self.max_clients:
                return None

            token = secrets.token_urlsafe(24)
            self._inflight.setdefault(key, {})[token] = now
            return token

    def finish_attempt(self, key, token, succeeded):
        """Finish only the specified attempt."""
        with self._lock:
            self._cleanup(time.monotonic())
            pending = self._inflight.get(key, {})

            if token not in pending:
                return False

            started = pending.pop(token)

            if not pending:
                self._inflight.pop(key, None)

            if succeeded:
                self._attempts.pop(key, None)
            else:
                now = time.monotonic()
                self._cleanup(now)
                timestamps = self._attempts.get(key, [])
                timestamps.append(started)
                self._attempts[key] = timestamps
                self._attempts.move_to_end(key)

                while len(self._attempts) > self.max_clients:
                    self._attempts.popitem(last=False)

            return True
