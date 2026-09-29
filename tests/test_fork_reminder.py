"""Oturum çatallama /fork (C10) ve tura-bağlı hatırlatma (C7)."""

from __future__ import annotations

from kuzgun.models import AssistantMessage, FakeModelClient


def test_fork_session_copies_history(make_engine):
    eng = make_engine([AssistantMessage(text="ok", tool_calls=[])] * 4)
    eng.chat("gizli bilgi 42", session_id="ana")
    eng.fork_session("ana", "kopya")
    h2 = eng.history("kopya")
    assert any("gizli bilgi 42" in m.get("content", "") for m in h2)
    # Kopya bağımsız: kopyaya ekleme anaya sızmaz.
    eng.chat("kopyaya özel", session_id="kopya")
    h1 = eng.history("ana")
    assert not any("kopyaya özel" in m.get("content", "") for m in h1)


def test_fork_from_default_session(make_engine):
    eng = make_engine([AssistantMessage(text="ok", tool_calls=[])] * 4)
    eng.chat("varsayılan konuşma")
    eng.fork_session(None, "yeni")
    assert any("varsayılan konuşma" in m.get("content", "") for m in eng.history("yeni"))


class _RecordingClient:
    def __init__(self, text):
        self.text = text
        self.seen_contents = []

    def chat(self, messages, tools):
        self.seen_contents.append([m.get("content", "") for m in messages])
        return AssistantMessage(text=self.text, tool_calls=[])


def test_turn_reminder_seen_by_model_but_not_persisted(make_engine):
    eng = make_engine()
    rec = _RecordingClient("cevap")
    eng.client = rec
    eng.coder_client = rec
    eng.chat("normal soru", reminder="çok kısa cevap ver")
    # Model çağrısında hatırlatma bağlamda vardı:
    all_seen = " ".join(c for call in rec.seen_contents for c in call)
    assert "çok kısa cevap ver" in all_seen
    # Ama kalıcı geçmişe girmedi (tura özgü):
    assert not any("çok kısa cevap ver" in m.get("content", "") for m in eng.messages)
