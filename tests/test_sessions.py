"""SessionStore: oturum izolasyonu, kilit, TTL ve üst sınır (Faz A4)."""

from __future__ import annotations

import threading

from kuzgun.sessions import SessionStore


def test_get_creates_and_returns_same_list():
    s = SessionStore(factory=list)
    a = s.get("x")
    a.append(1)
    assert s.get("x") == [1]          # aynı oturum aynı listeyi verir
    assert s.get("y") == []           # farklı oturum ayrı liste


def test_lock_is_per_session():
    s = SessionStore(factory=list)
    assert s.lock("a") is s.lock("a")     # aynı oturum -> aynı kilit
    assert s.lock("a") is not s.lock("b")  # farklı oturum -> farklı kilit


def test_drop_removes_session():
    s = SessionStore(factory=list)
    s.get("a")
    s.drop("a")
    assert "a" not in s.sessions


def test_ttl_evicts_stale_sessions():
    now = [1000.0]
    s = SessionStore(factory=list, ttl_seconds=10, clock=lambda: now[0])
    s.get("eski")
    now[0] += 100                     # TTL aşıldı
    s.get("yeni")                     # erişim eviction tetikler
    assert "eski" not in s.sessions
    assert "yeni" in s.sessions


def test_cap_evicts_least_recently_used():
    now = [0.0]
    s = SessionStore(factory=list, max_sessions=2, clock=lambda: now[0])
    for sid in ("a", "b"):
        now[0] += 1
        s.get(sid)
    now[0] += 1
    s.get("a")                        # a'ya tekrar erişim -> b en eski olur
    now[0] += 1
    s.get("c")                        # kapasite aşıldı -> b atılır
    assert "b" not in s.sessions
    assert "a" in s.sessions and "c" in s.sessions


def test_concurrent_same_session_not_corrupted(make_engine):
    # A4 (bug #10): aynı oturuma eşzamanlı chat çağrıları geçmişi bozmamalı.
    from kuzgun.models import AssistantMessage, FakeModelClient

    eng = make_engine()
    # Her thread kendi mesajını verir; sınırsız cevap üreten client.

    class _Client:
        def chat(self, messages, tools):
            return AssistantMessage(text="ok", tool_calls=[])

    eng.client = _Client()
    eng.coder_client = _Client()

    errors = []

    def worker(i):
        try:
            eng.chat(f"mesaj {i}", session_id="ortak")
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    hist = eng.history("ortak")
    users = [m for m in hist if m.get("role") == "user"]
    assistants = [m for m in hist if m.get("role") == "assistant"]
    # Kırpma sınırı içinde: her user mesajını bir assistant izler (torn/sarkan yok).
    assert len(users) == len(assistants)
    _ = FakeModelClient  # import kullanımı
