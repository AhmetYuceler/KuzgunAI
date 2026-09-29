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


def _mutating_registry():
    reg = ToolRegistry()
    calls = []
    schema = {
        "type": "function",
        "function": {"name": "yaz", "parameters": {"type": "object", "properties": {}}},
    }
    reg.register(schema, lambda: calls.append("x") or "yazildi", mutating=True)
    return reg, calls


def test_confirm_allows_mutation_in_normal_mode():
    reg, calls = _mutating_registry()
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
    out = eng.chat("yaz bir sey", mode="normal", confirm=lambda n, a: True)
    assert out == "bitti"
    assert calls == ["x"]  # confirm=True -> araç çalıştı


def test_sessions_are_isolated():
    eng = KuzgunEngine(
        client=FakeModelClient([AssistantMessage(text="ok", tool_calls=[])] * 10),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
    )
    eng.chat("s1 ozel mesaj", session_id="s1")
    eng.chat("s2 ozel mesaj", session_id="s2")
    h1 = eng.history("s1")
    assert any("s1 ozel mesaj" in m.get("content", "") for m in h1)
    assert not any("s2 ozel mesaj" in m.get("content", "") for m in h1)


def _echo_registry():
    reg = ToolRegistry()
    schema = {
        "type": "function",
        "function": {
            "name": "echo",
            "parameters": {"type": "object", "properties": {"text": {"type": "string"}}},
        },
    }
    reg.register(schema, lambda text="": f"ARAC:{text}")
    return reg


def test_engine_escalates_when_stuck_and_learns():
    loop = AssistantMessage(text=None, tool_calls=[ToolCall("1", "echo", {"text": "x"})])
    eng = KuzgunEngine(
        client=FakeModelClient([loop] * 20),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=_echo_registry(),
        escalate=lambda q: "CLAUDE CEVABI",
    )
    out = eng.chat("zor soru")
    assert out == "CLAUDE CEVABI"
    assert eng.memory.count() == 1  # devredilen cevap hafızaya yazıldı (öğrenme)


def test_autoroute_hard_task_goes_to_expert():
    # 'react ... kur' açıkça zor -> yerel model hiç çağrılmadan uzmana gitmeli.
    eng = KuzgunEngine(
        client=FakeModelClient([]),  # çağrılırsa IndexError verir
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
        escalate=lambda q: "UZMAN CEVABI",
    )
    out = eng.chat("bana bir react uygulaması kur")
    assert out == "UZMAN CEVABI"
    assert eng.memory.count() == 1  # öğrenildi


def test_autoroute_easy_task_uses_local():
    eng = KuzgunEngine(
        client=FakeModelClient([AssistantMessage(text="yerel cevap", tool_calls=[])]),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
        escalate=lambda q: "UZMAN",
    )
    assert eng.chat("merhaba nasılsın") == "yerel cevap"


def test_autoroute_can_be_disabled():
    from kuzgun.config import Config

    eng = KuzgunEngine(
        client=FakeModelClient([AssistantMessage(text="yerel", tool_calls=[])]),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
        escalate=lambda q: "UZMAN",
        config=Config(autoroute=False),
    )
    assert eng.chat("react uygulaması kur") == "yerel"  # autoroute kapalı -> yerel


def test_history_is_trimmed():
    eng = KuzgunEngine(
        client=FakeModelClient([AssistantMessage(text="x", tool_calls=[])] * 200),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
    )
    for i in range(80):
        eng.chat(f"mesaj {i}")
    assert len(eng.messages) <= eng.MAX_HISTORY
    assert eng.messages[0]["role"] == "system"


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
