from kuzgun.engine import KuzgunEngine
from kuzgun.embeddings import FakeEmbedder
from kuzgun.memory import Memory
from kuzgun.models import AssistantMessage, ToolCall, FakeModelClient
from kuzgun.tools import ToolRegistry


def _engine(scripted, registry=None):
    return KuzgunEngine(
        client=FakeModelClient(scripted),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=registry if registry is not None else ToolRegistry(),
    )


def test_chat_direct_answer():
    eng = _engine([AssistantMessage(text="merhaba", tool_calls=[])])
    assert eng.chat("selam") == "merhaba"


def test_engine_uses_config_db_path(monkeypatch, tmp_path):
    monkeypatch.setenv("KUZGUN_DB", str(tmp_path / "x.db"))
    eng = KuzgunEngine(client=FakeModelClient([]), embedder=FakeEmbedder())
    assert eng.config.db_path == str(tmp_path / "x.db")
    assert eng.memory.count() == 0  # config yolundaki gerçek dosya


def test_chat_saves_to_memory():
    eng = _engine([AssistantMessage(text="cevap", tool_calls=[])])
    eng.chat("soru")
    assert eng.memory.count() == 1


def test_normal_mode_denies_mutation_without_confirm():
    reg = ToolRegistry()
    calls = []
    schema = {
        "type": "function",
        "function": {"name": "yaz", "parameters": {"type": "object", "properties": {}}},
    }
    reg.register(schema, lambda: calls.append("x") or "yazildi", mutating=True)
    eng = _engine(
        [
            AssistantMessage(text=None, tool_calls=[ToolCall("1", "yaz", {})]),
            AssistantMessage(text="bitti", tool_calls=[]),
        ],
        registry=reg,
    )
    out = eng.chat("yaz bir sey", mode="normal")
    assert out == "bitti"
    assert calls == []  # confirm yok -> reddedildi (güvenli)
