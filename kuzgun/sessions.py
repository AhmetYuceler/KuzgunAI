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
        self._active: dict[str, int] = {}  # tur ortasındaki (pinli) oturumlar → atılamaz
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

    def pin(self, sid: str) -> None:
        """Oturumu 'tur ortasında' işaretle: eviction bu oturumu atamaz ve kilidini
        yok edemez (aksi halde eşzamanlı ikinci tur yeni kilit uydurur — bug #10).
        Oturum+kilit yoksa oluşturur ki tur boyunca sabit kalsın. Yeniden girişe
        dayanıklı (sayaç)."""
        with self._guard:
            if sid not in self.sessions:
                self.sessions[sid] = self._factory()
                self._locks[sid] = threading.Lock()
            self._seen[sid] = self._clock()
            self._active[sid] = self._active.get(sid, 0) + 1

    def unpin(self, sid: str) -> None:
        with self._guard:
            n = self._active.get(sid, 0) - 1
            if n <= 0:
                self._active.pop(sid, None)
            else:
                self._active[sid] = n

    def drop(self, sid: str) -> None:
        with self._guard:
            self.sessions.pop(sid, None)
            self._locks.pop(sid, None)
            self._seen.pop(sid, None)
            self._active.pop(sid, None)

    def _forget(self, sid: str) -> None:
        self.sessions.pop(sid, None)
        self._locks.pop(sid, None)
        self._seen.pop(sid, None)

    def _protected(self, keep: str | None) -> set[str]:
        # Atılamayacak oturumlar: şu an erişilen (keep) + tur ortasındaki (pinli) hepsi.
        prot = set(self._active)
        if keep is not None:
            prot.add(keep)
        return prot

    def _evict_locked(self, keep: str | None = None) -> None:
        now = self._clock()
        protected = self._protected(keep)
        for sid in [
            s for s, t in self._seen.items() if now - t > self._ttl and s not in protected
        ]:
            self._forget(sid)
        # Üst sınır: en eski erişilen (LRU) oturumları at (korunanlar hariç).
        while len(self.sessions) > self._max:
            candidates = {s: t for s, t in self._seen.items() if s not in protected}
            if not candidates:
                break  # kalanların hepsi korunuyor → sınır geçici olarak aşılabilir
            self._forget(min(candidates, key=candidates.__getitem__))
