"""Oturumlar-arası mesaj kutusu (Faz C11).

Claude'un cross-session mesajlaşmasının güvenlik modeli birebir: gelen mesaj
KULLANICI YETKİSİ TAŞIMAZ — yalnızca veridir (onay veremez, ayar/mod değiştiremez,
komut çalıştıramaz). Alıcı oturum mesajı bilgi olarak değerlendirir. Döngü koruması:
gönderici başına hız sınırı, aynı mesajın kopyasını düşürme, kuyruk üst sınırı.
"""

from __future__ import annotations

import threading
import time
from collections import deque


class Inbox:
    def __init__(
        self,
        max_queue: int = 50,
        rate_limit: int = 20,
        window: float = 60.0,
        dedup_window: float = 60.0,
        clock=time.monotonic,
    ):
        self._max_queue = max_queue
        self._rate_limit = rate_limit
        self._window = window
        self._dedup_window = dedup_window
        self._clock = clock
        self._queues: dict[str, deque] = {}
        self._sender_times: dict[str, deque] = {}
        self._recent: dict[tuple, float] = {}
        self._lock = threading.Lock()

    def send(self, to_session: str, from_session: str, text: str) -> bool:
        """Mesajı alıcının kutusuna koyar. Kabul edilirse True; hız sınırı/kopya
        nedeniyle reddedilirse False."""
        now = self._clock()
        with self._lock:
            # Hız sınırı: gönderici başına pencere içinde en fazla rate_limit.
            times = self._sender_times.setdefault(from_session, deque())
            while times and now - times[0] > self._window:
                times.popleft()
            if len(times) >= self._rate_limit:
                return False
            # Kopya düşürme: aynı (alıcı, gönderici, metin) yakın zamanda geldiyse at.
            key = (to_session, from_session, text)
            self._recent = {k: t for k, t in self._recent.items() if now - t <= self._dedup_window}
            if key in self._recent:
                return False
            # Kabul.
            times.append(now)
            self._recent[key] = now
            q = self._queues.setdefault(to_session, deque(maxlen=self._max_queue))
            q.append({"from": from_session, "text": text, "ts": now})
            return True

    def poll(self, session: str) -> list[dict]:
        """Oturumun bekleyen mesajlarını döndürür ve kutusunu boşaltır (drenaj)."""
        with self._lock:
            q = self._queues.get(session)
            if not q:
                return []
            msgs = list(q)
            q.clear()
            return msgs

    def pending(self, session: str) -> int:
        with self._lock:
            q = self._queues.get(session)
            return len(q) if q else 0
