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
