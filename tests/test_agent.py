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
