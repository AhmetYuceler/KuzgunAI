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


def test_engine_loads_notes_into_context(tmp_path):
    from kuzgun.config import Config

    notes = tmp_path / "KUZGUN.md"
    notes.write_text("- kullanıcının adı Ahmet\n- mavi rengi sever\n", encoding="utf-8")
    eng = KuzgunEngine(
        client=FakeModelClient([]),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
        config=Config(notes_path=str(notes)),
    )
    assert any("Ahmet" in m.get("content", "") for m in eng.messages)


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


def _notes_engine(tmp_path, scripted):
    from kuzgun.config import Config

    notes = tmp_path / "KUZGUN.md"
    eng = KuzgunEngine(
        client=FakeModelClient(scripted),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
        config=Config(notes_path=str(notes)),
    )
    return eng, notes


def test_trim_keeps_notes_in_context(tmp_path):
    from kuzgun.config import Config

    notes = tmp_path / "KUZGUN.md"
    notes.write_text("- kullanıcının adı Ahmet\n", encoding="utf-8")
    eng = KuzgunEngine(
        client=FakeModelClient([AssistantMessage(text="x", tool_calls=[])] * 200),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
        config=Config(notes_path=str(notes)),
    )
    for i in range(80):
        eng.chat(f"mesaj {i}")
    assert len(eng.messages) <= eng.MAX_HISTORY
    assert any("Ahmet" in m.get("content", "") for m in eng.messages)  # kırpma notu silmez


def test_new_note_reaches_running_conversation(tmp_path):
    eng, notes = _notes_engine(tmp_path, [AssistantMessage(text="x", tool_calls=[])] * 3)
    eng.chat("merhaba")
    notes.write_text("- mavi rengi sever\n", encoding="utf-8")  # /hatirla ya da remember aracı
    eng.chat("nasılsın")
    hits = [m for m in eng.messages if "mavi rengi" in m.get("content", "")]
    assert len(hits) == 1  # süren konuşmaya girdi, tekrarlanmadı
    eng.chat("peki")
    assert len([m for m in eng.messages if "mavi rengi" in m.get("content", "")]) == 1


def test_new_note_reaches_new_sessions(tmp_path):
    eng, notes = _notes_engine(tmp_path, [])
    notes.write_text("- mavi rengi sever\n", encoding="utf-8")
    assert any("mavi rengi" in m.get("content", "") for m in eng.history("yeni"))


def test_run_agents_cleans_up_worker_sessions():
    client = FakeModelClient(
        [
            AssistantMessage(text='["ilk is", "ikinci is"]', tool_calls=[]),
            AssistantMessage(text="ilk sonuc", tool_calls=[]),
            AssistantMessage(text="ikinci sonuc", tool_calls=[]),
            AssistantMessage(text="birlesik cevap", tool_calls=[]),
        ]
    )
    eng = KuzgunEngine(
        client=client,
        coder_client=client,
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
    )
    eng.run_agents("iki isi de yap")
    assert eng._sessions == {}  # işçi oturumları birikmez


def test_engine_weather_only_message_skips_model(monkeypatch):
    import kuzgun.engine as eng_mod

    monkeypatch.setattr(eng_mod, "weather", lambda: "Kayseri: +15°C")
    eng = _engine([])  # model çağrılırsa IndexError
    assert "Kayseri" in eng.chat("bugün hava nasıl?")


def test_engine_compound_weather_message_still_asks_model(monkeypatch):
    # Ekran görüntüsündeki hata: 'hava kaç derece? 2x2 kaç? başkent neresi' →
    # yalnız hava cevaplanıyor, diğer sorular yutuluyordu.
    import kuzgun.engine as eng_mod

    monkeypatch.setattr(eng_mod, "weather", lambda: "Kayseri: +15°C")
    client = FakeModelClient([AssistantMessage(text="4 ve Ankara", tool_calls=[])])
    eng = KuzgunEngine(
        client=client, embedder=FakeEmbedder(), memory=Memory(":memory:"), registry=ToolRegistry()
    )
    out = eng.chat("hava kaç derece şu anda? 2x2 kaç? türkiye başkenti neresi")
    assert out == "4 ve Ankara"
    # hava durumu modele bağlam olarak verildi
    assert any(m["role"] == "system" and "Kayseri" in m["content"] for m in eng.messages)


def test_chat_with_images_two_stage_describe_then_answer_with_tools(tmp_path):
    """Görsel model resmi BETİMLER (kimlik tahmini yok); soruyu araçlı metin ajanı
    cevaplar (web_search yapabilsin). Betimleme geçmişe girer → sonraki mesajlar
    resmi 'hatırlar'."""
    img = tmp_path / "ekran.png"
    img.write_bytes(b"\x89PNG")
    seen = {}

    class VisionClient:
        def chat(self, messages, tools):
            seen["messages"] = messages
            seen["tools"] = tools
            return AssistantMessage(text="Garajda, yüzünde morluk olan bir kadın; Ford yazısı", tool_calls=[])

    text_client = FakeModelClient(
        [
            AssistantMessage(text="İpuçlarına göre bu Ironheart olabilir.", tool_calls=[]),
            AssistantMessage(text="Evet, Ironheart (2025).", tool_calls=[]),
        ]
    )
    eng = KuzgunEngine(
        client=text_client,
        vision_client=VisionClient(),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
    )
    out = eng.chat("[resim 1] bu film hangi film?", images=[str(img)])
    assert out == "İpuçlarına göre bu Ironheart olabilir."  # cevap metin ajanından
    assert not seen["tools"]  # görsel modele araç verilmez
    from kuzgun.engine import VISION_PROMPT

    assert seen["messages"][0] == {"role": "system", "content": VISION_PROMPT}
    vis_user = seen["messages"][-1]
    assert isinstance(vis_user["content"], list) and vis_user["content"][1]["type"] == "image_url"
    assert "[resim 1]" not in vis_user["content"][0]["text"]  # kutu etiketi modele gitmez
    # Betimleme geçmişte sistem notu olarak durur; kullanıcı mesajı metin + dosya adı
    notes = [m for m in eng.messages if m["role"] == "system" and "morluk" in m["content"]]
    assert notes and "ekran.png" in notes[0]["content"]
    hist_user = [m for m in eng.messages if m["role"] == "user"][-1]
    assert isinstance(hist_user["content"], str) and "ekran.png" in hist_user["content"]
    assert eng.memory.count() == 1
    # Resimsiz devam mesajı: betimleme hâlâ bağlamda, görsel model tekrar çağrılmaz
    seen.clear()
    assert eng.chat("dizi aslında bir marvel dizisi, hangisi?") == "Evet, Ironheart (2025)."
    assert not seen
    assert any("morluk" in m["content"] for m in eng.messages if m["role"] == "system")
