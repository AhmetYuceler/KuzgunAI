from fastapi.testclient import TestClient

from kuzgun.config import Config
from kuzgun.embeddings import FakeEmbedder
from kuzgun.engine import KuzgunEngine
from kuzgun.memory import Memory
from kuzgun.models import AssistantMessage, FakeModelClient
from kuzgun.server import create_app
from kuzgun.tools import ToolRegistry


def _engine():
    return KuzgunEngine(
        client=FakeModelClient([AssistantMessage(text="merhaba", tool_calls=[])] * 10),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
    )


def _client(config=None):
    app = create_app(_engine(), config=config or Config())
    return TestClient(app, base_url="http://127.0.0.1")


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
    assert r.status_code == 422


def test_rejects_untrusted_host():
    # Host allow-list dışı (DNS-rebinding koruması) -> 400
    app = create_app(_engine(), config=Config())
    c = TestClient(app, base_url="http://evil.example.com")
    assert c.get("/health").status_code == 400


def test_token_required_when_configured():
    c = _client(config=Config(token="gizli"))
    # token yok -> 401
    assert c.post("/chat", json={"message": "selam"}).status_code == 401
    # doğru token -> 200
    r = c.post(
        "/chat",
        json={"message": "selam"},
        headers={"Authorization": "Bearer gizli"},
    )
    assert r.status_code == 200
