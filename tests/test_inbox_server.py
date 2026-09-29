"""Oturumlar-arası mesajlaşma HTTP uçları (Faz C11)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from kuzgun.config import Config
from kuzgun.embeddings import FakeEmbedder
from kuzgun.engine import KuzgunEngine
from kuzgun.memory import Memory
from kuzgun.models import FakeModelClient
from kuzgun.server import create_app
from kuzgun.tools import ToolRegistry


def _client():
    cfg = Config(allowed_hosts="testserver,localhost,127.0.0.1")
    eng = KuzgunEngine(
        client=FakeModelClient([]),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
        config=cfg,
    )
    return TestClient(create_app(eng, cfg))


def test_inbox_send_and_poll_over_http():
    c = _client()
    r = c.post("/inbox/send", json={"to": "b", "from": "a", "text": "selam"})
    assert r.status_code == 200 and r.json()["accepted"] is True
    r2 = c.post("/inbox/poll", json={"session": "b"})
    msgs = r2.json()["messages"]
    assert len(msgs) == 1 and msgs[0]["from"] == "a" and msgs[0]["text"] == "selam"


def test_inbox_poll_empty():
    c = _client()
    r = c.post("/inbox/poll", json={"session": "yok"})
    assert r.json()["messages"] == []
