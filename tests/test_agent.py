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
