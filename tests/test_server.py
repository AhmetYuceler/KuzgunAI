from fastapi.testclient import TestClient

from kuzgun.config import Config
from kuzgun.embeddings import FakeEmbedder
from kuzgun.engine import KuzgunEngine
from kuzgun.memory import Memory
from kuzgun.models import AssistantMessage, FakeModelClient, ToolCall
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


def test_memory_persists_through_server_threadpool():
    # C1 regresyon: sunucu isteği iş parçacığından koşar; hafıza gerçekten kaydetmeli.
    from kuzgun.memory import Memory

    eng = KuzgunEngine(
        client=FakeModelClient([AssistantMessage(text="merhaba", tool_calls=[])] * 10),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
    )
    c = TestClient(create_app(eng, config=Config()), base_url="http://127.0.0.1")
    r = c.post("/chat", json={"message": "selam"})
    assert r.status_code == 200
    assert eng.memory.count() == 1  # threadpool'dan kaydedildi (eskiden sessizce 0'dı)


def test_server_clamps_otonom_to_prevent_rce():
    # İstemci 'otonom' gönderse bile sunucu değişiklik yapan aracı ÇALIŞTIRMAMALI.
    from kuzgun.memory import Memory

    reg = ToolRegistry()
    calls = []
    schema = {
        "type": "function",
        "function": {"name": "yaz", "parameters": {"type": "object", "properties": {}}},
    }
    reg.register(schema, lambda: calls.append("x") or "ok", mutating=True)
    eng = KuzgunEngine(
        client=FakeModelClient(
            [
                AssistantMessage(text=None, tool_calls=[ToolCall("1", "yaz", {})]),
                AssistantMessage(text="bitti", tool_calls=[]),
            ]
        ),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=reg,
    )
    c = TestClient(create_app(eng, config=Config()), base_url="http://127.0.0.1")
    r = c.post("/chat", json={"message": "yaz bir sey", "mode": "otonom"})
    assert r.status_code == 200
    assert calls == []  # RCE önlendi: otonom istemciden gelse bile mutasyon koşmadı


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
