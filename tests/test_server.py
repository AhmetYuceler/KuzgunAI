from fastapi.testclient import TestClient

from kuzgun.embeddings import FakeEmbedder
from kuzgun.engine import KuzgunEngine
from kuzgun.memory import Memory
from kuzgun.models import AssistantMessage, FakeModelClient
from kuzgun.server import create_app
from kuzgun.tools import ToolRegistry


def _client():
    eng = KuzgunEngine(
        client=FakeModelClient([AssistantMessage(text="merhaba", tool_calls=[])] * 10),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
    )
    return TestClient(create_app(eng))


def test_health():
    r = _client().get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_chat_returns_reply():
    r = _client().post("/chat", json={"message": "selam"})
    assert r.status_code == 200
    assert r.json()["reply"] == "merhaba"


def test_chat_requires_message():
    r = _client().post("/chat", json={})
    assert r.status_code == 422  # eksik alan
