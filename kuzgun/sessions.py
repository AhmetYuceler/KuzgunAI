"""Oturum deposu (Faz A4).

Her oturum (session_id) kendi konuşma geçmişini ve kendi kilidini tutar. Kilit
tur boyunca tutulunca aynı oturuma eşzamanlı iki istek birbirinin geçmişini
bozmaz (bug #10). TTL ve üst sınır ile depo sınırsız büyümez; en eski (LRU)
oturumlar atılır. `ajan-*` işçi oturumları iş bitince drop() ile temizlenir.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class SessionStore:
    def __init__(
        self,
        factory: Callable[[], list],
        max_sessions: int = 200,
        ttl_seconds: float = 3600,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._factory = factory
        self._max = max_sessions
        self._ttl = ttl_seconds
        self._clock = clock
        self.sessions: dict[str, list] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._seen: dict[str, float] = {}
        self._guard = threading.Lock()

    def get(self, sid: str) -> list:
        """Oturumun geçmiş listesini döndürür (yoksa oluşturur). Erişim zamanını
        günceller ve eskimiş/aşan oturumları temizler."""
        with self._guard:
            if sid not in self.sessions:
                self.sessions[sid] = self._factory()
                self._locks[sid] = threading.Lock()
            self._seen[sid] = self._clock()
            self._evict_locked(keep=sid)
            return self.sessions[sid]

    def lock(self, sid: str) -> threading.Lock:
        """Oturuma özgü kilit (tur boyunca tutulur)."""
        with self._guard:
            lk = self._locks.get(sid)
            if lk is None:
                lk = self._locks[sid] = threading.Lock()
            return lk

    def drop(self, sid: str) -> None:
        with self._guard:
            self.sessions.pop(sid, None)
            self._locks.pop(sid, None)
            self._seen.pop(sid, None)

    def _forget(self, sid: str) -> None:
        self.sessions.pop(sid, None)
        self._locks.pop(sid, None)
        self._seen.pop(sid, None)

    def _evict_locked(self, keep: str | None = None) -> None:
        now = self._clock()
        for sid in [s for s, t in self._seen.items() if now - t > self._ttl and s != keep]:
            self._forget(sid)
        # Üst sınır: en eski erişilen (LRU) oturumları at (aktif oturum korunur).
        while len(self.sessions) > self._max:
            candidates = {s: t for s, t in self._seen.items() if s != keep}
            if not candidates:
                break
            self._forget(min(candidates, key=candidates.__getitem__))
