import pytest

from kuzgun.agent import run_turn
from kuzgun.models import AssistantMessage, ToolCall, FakeModelClient
from kuzgun.tools import ToolRegistry


def _registry_with_echo():
    reg = ToolRegistry()
    schema = {
        "type": "function",
        "function": {
            "name": "echo",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    }
    reg.register(schema, lambda text: f"ARAC: {text}")
    return reg


def test_direct_answer_without_tools():
    client = FakeModelClient([AssistantMessage(text="direkt cevap", tool_calls=[])])
    out = run_turn(client, [{"role": "user", "content": "selam"}], ToolRegistry())
    assert out == "direkt cevap"


def test_calls_tool_then_answers():
    client = FakeModelClient([
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "echo", {"text": "x"})]),
        AssistantMessage(text="arac calisti", tool_calls=[]),
    ])
    messages = [{"role": "user", "content": "echo x"}]
    out = run_turn(client, messages, _registry_with_echo())
    assert out == "arac calisti"
    # gecmiste bir tool sonucu bulunmali
    assert any(
        m.get("role") == "tool" and "ARAC: x" in m.get("content", "") for m in messages
    )


def test_unknown_tool_does_not_crash():
    client = FakeModelClient([
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "yok", {})]),
        AssistantMessage(text="devam", tool_calls=[]),
    ])
    out = run_turn(client, [{"role": "user", "content": "?"}], ToolRegistry())
    assert out == "devam"


def test_max_steps_guard():
    # surekli arac isteyen model -> RuntimeError
    loop_msg = AssistantMessage(text=None, tool_calls=[ToolCall("1", "echo", {"text": "x"})])
    client = FakeModelClient([loop_msg] * 20)
    with pytest.raises(RuntimeError):
        run_turn(client, [{"role": "user", "content": "?"}], _registry_with_echo(), max_steps=3)


def test_escalates_on_repeated_identical_tool_call():
    # Model aynı araç çağrısını tekrarlıyor (döngü) -> otonom devretme çağrılmalı
    loop_msg = AssistantMessage(text=None, tool_calls=[ToolCall("1", "echo", {"text": "x"})])
    client = FakeModelClient([loop_msg] * 20)
    escalated = {}

    def escalate(question):
        escalated["q"] = question
        return "UZMAN CEVABI"

    out = run_turn(
        client,
        [{"role": "user", "content": "zor soru"}],
        _registry_with_echo(),
        max_steps=10,
        escalate=escalate,
    )
    assert out == "UZMAN CEVABI"
    assert "zor soru" in escalated["q"]


def test_escalates_on_max_steps_when_escalate_given():
    loop_msg = AssistantMessage(text=None, tool_calls=[ToolCall("1", "echo", {"text": "x"})])
    # Her adımda argüman değişsin ki döngü değil, sadece max_steps tetiklensin
    msgs = [
        AssistantMessage(text=None, tool_calls=[ToolCall(str(i), "echo", {"text": str(i)})])
        for i in range(20)
    ]
    client = FakeModelClient(msgs)
    out = run_turn(
        client,
        [{"role": "user", "content": "?"}],
        _registry_with_echo(),
        max_steps=3,
        escalate=lambda q: "DEVREDILDI",
    )
    assert out == "DEVREDILDI"


def test_budget_wrapup_summarizes_instead_of_raising():
    # C2: wrapup=True iken max_steps dolunca çökmez/Claude'a gitmez; yerel model
    # 'yaptıklarını özetle' turu yapıp kısmi cevap verir.
    steps = [
        AssistantMessage(text=None, tool_calls=[ToolCall(str(i), "echo", {"text": str(i)})])
        for i in range(3)  # max_steps kadar tool-call turu, sonra wrap-up turu
    ]
    wrapup = AssistantMessage(text="Şimdiye dek 3 adım yaptım, özet: ...", tool_calls=[])
    client = FakeModelClient([*steps, wrapup])
    messages = [{"role": "user", "content": "uzun görev"}]
    out = run_turn(client, messages, _registry_with_echo(), max_steps=3, wrapup=True)
    assert "özet" in out
    assert messages[-1] == {"role": "assistant", "content": out}


def test_max_steps_still_raises_without_wrapup_or_escalate():
    # Varsayılan (wrapup=False, escalate=None): eski davranış korunur (çöker).
    import pytest as _pytest
    loop = AssistantMessage(text=None, tool_calls=[ToolCall("1", "echo", {"text": "x"})])
    client = FakeModelClient([loop] * 20)
    with _pytest.raises(RuntimeError):
        run_turn(client, [{"role": "user", "content": "?"}], _registry_with_echo(), max_steps=3)


def test_legit_error_output_does_not_escalate():
    # B5: çıktısı "Error:" ile başlayan MEŞRU araç sonucu devretmeyi tetiklememeli.
    reg = ToolRegistry()
    reg.register(
        {"type": "function", "function": {"name": "api",
         "parameters": {"type": "object", "properties": {"q": {"type": "string"}}}}},
        lambda q="": "Error: 404 (gerçek API cevabı)",
    )
    client = FakeModelClient([
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "api", {"q": "a"})]),
        AssistantMessage(text=None, tool_calls=[ToolCall("2", "api", {"q": "b"})]),
        AssistantMessage(text="yerel cevap", tool_calls=[]),
    ])
    escalated = []
    out = run_turn(client, [{"role": "user", "content": "?"}], reg,
                   escalate=lambda q: escalated.append(q) or "UZMAN")
    assert out == "yerel cevap"     # devretme YOK (meşru çıktı hata sanılmadı)
    assert escalated == []


def test_large_tool_output_is_clipped_in_history():
    # B6: dev araç çıktısı 7B'nin küçük bağlamını doldurmasın; geçmişe kırpılmış girer.
    from kuzgun.agent import MAX_TOOL_CHARS

    reg = ToolRegistry()
    big = "A" * (MAX_TOOL_CHARS + 5000)
    reg.register(
        {"type": "function", "function": {"name": "buyuk",
         "parameters": {"type": "object", "properties": {}}}},
        lambda: big,
    )
    client = FakeModelClient([
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "buyuk", {})]),
        AssistantMessage(text="ok", tool_calls=[]),
    ])
    messages = [{"role": "user", "content": "?"}]
    run_turn(client, messages, reg)
    tool_msg = next(m for m in messages if m.get("role") == "tool")
    assert len(tool_msg["content"]) < len(big)          # kırpıldı
    assert "kırpıldı" in tool_msg["content"]             # kırpma notu var
    assert len(tool_msg["content"]) <= MAX_TOOL_CHARS + 200


def test_small_tool_output_not_clipped():
    reg = ToolRegistry()
    reg.register(
        {"type": "function", "function": {"name": "kucuk",
         "parameters": {"type": "object", "properties": {}}}},
        lambda: "kısa sonuç",
    )
    client = FakeModelClient([
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "kucuk", {})]),
        AssistantMessage(text="ok", tool_calls=[]),
    ])
    messages = [{"role": "user", "content": "?"}]
    run_turn(client, messages, reg)
    tool_msg = next(m for m in messages if m.get("role") == "tool")
    assert tool_msg["content"] == "kısa sonuç"


def test_escalated_reply_is_appended_to_history():
    # A3 (bug #5): run_turn uzmana devrederse, dönen cevap geçmişe de yazılmalı;
    # aksi halde bir sonraki tur bağlamında asistanın cevabı eksik kalır.
    loop_msg = AssistantMessage(text=None, tool_calls=[ToolCall("1", "echo", {"text": "x"})])
    client = FakeModelClient([loop_msg] * 20)
    messages = [{"role": "user", "content": "zor soru"}]
    out = run_turn(client, messages, _registry_with_echo(), escalate=lambda q: "UZMAN CEVABI")
    assert out == "UZMAN CEVABI"
    assert messages[-1] == {"role": "assistant", "content": "UZMAN CEVABI"}


def test_extract_wellformed_json_tool_call():
    from kuzgun.agent import extract_tool_calls_from_text

    txt = '```json\n{"name": "write_file", "arguments": {"path": "a.txt", "content": "hi"}}\n```'
    tcs = extract_tool_calls_from_text(txt)
    assert len(tcs) == 1
    assert tcs[0].name == "write_file"
    assert tcs[0].arguments["path"] == "a.txt"


def test_extract_handles_extra_trailing_brace():
    from kuzgun.agent import extract_tool_calls_from_text

    tcs = extract_tool_calls_from_text('{"name": "echo", "arguments": {"text": "x"}}}')
    assert len(tcs) == 1 and tcs[0].name == "echo"


def test_extract_plain_text_returns_empty():
    from kuzgun.agent import extract_tool_calls_from_text

    assert extract_tool_calls_from_text("merhaba nasılsın, bugün hava güzel") == []


def test_loop_executes_text_json_tool_call():
    # Model araç çağrısını gerçek çağrı yerine metin-json olarak verse bile çalışmalı.
    client = FakeModelClient(
        [
            AssistantMessage(text='{"name":"echo","arguments":{"text":"x"}}', tool_calls=[]),
            AssistantMessage(text="bitti", tool_calls=[]),
        ]
    )
    messages = [{"role": "user", "content": "?"}]
    out = run_turn(client, messages, _registry_with_echo())
    assert out == "bitti"
    assert any(
        m.get("role") == "tool" and "ARAC: x" in m.get("content", "")
        for m in messages
    )


def _spy_registry():
    """Çağrılınca kaydeden, değişiklik yapan (mutating) bir araç."""
    reg = ToolRegistry()
    calls = []
    schema = {
        "type": "function",
        "function": {
            "name": "yaz",
            "parameters": {"type": "object", "properties": {"x": {"type": "string"}}},
        },
    }
    reg.register(schema, lambda x="": calls.append(x) or "yazildi", mutating=True)
    return reg, calls


def test_plan_mode_blocks_mutating_tool():
    reg, calls = _spy_registry()
    client = FakeModelClient([
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "yaz", {"x": "a"})]),
        AssistantMessage(text="tamam", tool_calls=[]),
    ])
    messages = [{"role": "user", "content": "?"}]
    out = run_turn(client, messages, reg, mode="plan")
    assert out == "tamam"
    assert calls == []  # araç ÇALIŞMAMALI
    assert any(
        "plan modu" in m.get("content", "").lower()
        for m in messages
        if m.get("role") == "tool"
    )


def test_normal_mode_mutating_runs_when_confirmed():
    reg, calls = _spy_registry()
    client = FakeModelClient([
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "yaz", {"x": "a"})]),
        AssistantMessage(text="tamam", tool_calls=[]),
    ])
    run_turn(client, [{"role": "user", "content": "?"}], reg,
             mode="normal", confirm=lambda n, a: True)
    assert calls == ["a"]  # araç ÇALIŞTI


def test_normal_mode_mutating_blocked_without_confirm():
    reg, calls = _spy_registry()
    client = FakeModelClient([
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "yaz", {"x": "a"})]),
        AssistantMessage(text="tamam", tool_calls=[]),
    ])
    run_turn(client, [{"role": "user", "content": "?"}], reg, mode="normal", confirm=None)
    assert calls == []


def test_text_json_with_unknown_tool_is_plain_answer():
    # Cevabın kendisi JSON ise (kayıtlı bir araç adı değil) araç çağrısı sanılmamalı.
    txt = '{"name": "Ahmet", "arguments": {"yas": 30}}'
    client = FakeModelClient([AssistantMessage(text=txt, tool_calls=[])])
    messages = [{"role": "user", "content": "bana örnek json ver"}]
    out = run_turn(client, messages, _registry_with_echo())
    assert out == txt
    assert not any(m.get("role") == "tool" for m in messages)


def test_pseudo_python_call_in_text_is_recovered():
    # Görsel akışında gözlendi: model aracı çağırmak yerine satır olarak yazıyor.
    from kuzgun.agent import extract_tool_calls_from_text

    text = 'Emin olmak için araştıralım.\n web_search(query="Claude Code v2.1.284 Fable 5.1")\n'
    calls = extract_tool_calls_from_text(text)
    assert len(calls) == 1
    assert calls[0].name == "web_search"
    assert calls[0].arguments == {"query": "Claude Code v2.1.284 Fable 5.1"}


def test_pseudo_call_parses_numbers_bools_and_single_quotes():
    from kuzgun.agent import extract_tool_calls_from_text

    calls = extract_tool_calls_from_text("read_file(path='a.txt', max_lines=10, raw=true)")
    assert calls[0].arguments == {"path": "a.txt", "max_lines": 10, "raw": True}


def test_pseudo_call_ignores_code_blocks_and_prose():
    from kuzgun.agent import extract_tool_calls_from_text

    assert extract_tool_calls_from_text("```python\nprint(x)\n```") == []
    assert extract_tool_calls_from_text("topla(a, b) fonksiyonu iki sayıyı toplar") == []
    assert extract_tool_calls_from_text("Sonuç: f(x)=3") == []
