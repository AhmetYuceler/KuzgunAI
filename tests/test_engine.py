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


def test_code_task_uses_coder_client():
    general = FakeModelClient([AssistantMessage(text="GENEL", tool_calls=[])])
    coder = FakeModelClient([AssistantMessage(text="KODER", tool_calls=[])])
    eng = KuzgunEngine(
        client=general,
        coder_client=coder,
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
    )
    assert eng.chat("Python'da iki sayiyi toplayan bir fonksiyon yaz") == "KODER"


def test_general_task_uses_general_client():
    general = FakeModelClient([AssistantMessage(text="GENEL", tool_calls=[])])
    coder = FakeModelClient([AssistantMessage(text="KODER", tool_calls=[])])
    eng = KuzgunEngine(
        client=general,
        coder_client=coder,
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
    )
    assert eng.chat("merhaba nasılsın") == "GENEL"


def test_reflect_fixes_broken_code():
    from kuzgun.verify import check_python_syntax, extract_code_blocks

    client = FakeModelClient(
        [
            AssistantMessage(text="```python\ndef f(:\n    return 1\n```", tool_calls=[]),
            AssistantMessage(text="```python\ndef f():\n    return 1\n```", tool_calls=[]),
        ]
    )
    eng = KuzgunEngine(
        client=client,
        coder_client=client,
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
    )
    out = eng.chat("Python'da bir f fonksiyonu yaz")
    ok, _ = check_python_syntax(extract_code_blocks(out)[0])
    assert ok  # yansıtma sonrası kod sözdizimsel geçerli


def test_no_reflect_when_code_valid():
    # Geçerli kodda ikinci (düzeltme) çağrısı yapılmamalı (aksi halde IndexError).
    client = FakeModelClient([AssistantMessage(text="```python\nx = 1\n```", tool_calls=[])])
    eng = KuzgunEngine(
        client=client,
        coder_client=client,
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
    )
    assert "x = 1" in eng.chat("python ile x'e 1 ata")


def test_engine_handles_media_intent_directly(monkeypatch):
    import kuzgun.engine as eng_mod

    calls = []
    monkeypatch.setattr(eng_mod, "media_control", lambda action: calls.append(action) or f"Medya: {action}")
    eng = KuzgunEngine(
        client=FakeModelClient([]),  # model çağrılırsa IndexError
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
    )
    out = eng.chat("spotifydan müziği değiştir", mode="normal")
    assert calls == ["next"]  # doğrudan media_control, model kullanılmadı
    assert "Medya" in out


def test_run_agents_decomposes_and_synthesizes():
    client = FakeModelClient(
        [
            AssistantMessage(text='["ilk is", "ikinci is"]', tool_calls=[]),  # plan
            AssistantMessage(text="ilk sonuc", tool_calls=[]),  # işçi-ajan 1
            AssistantMessage(text="ikinci sonuc", tool_calls=[]),  # işçi-ajan 2
            AssistantMessage(text="birlesik cevap", tool_calls=[]),  # sentez
        ]
    )
    eng = KuzgunEngine(
        client=client,
        coder_client=client,
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
    )
    assert eng.run_agents("iki isi de yap") == "birlesik cevap"


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
