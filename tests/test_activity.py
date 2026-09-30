"""Canlı 'ne yapıyor' aktivite satırları (Claude Code'un tool-call kartları gibi):
her araç çağrısı ve sonucu, sorunun altına kalıcı bir satır olarak transcript'e yazılır.
Buradaki testler saf biçimlendiricileri ve run_turn'ün 'tool'/'result' olaylarını doğrular.
"""

from __future__ import annotations

from kuzgun.agent import (
    _arg_summary,
    _oneline,
    _result_summary,
    _tool_activity,
    run_turn,
)
from kuzgun.models import AssistantMessage, FakeModelClient, ToolCall
from kuzgun.tools import ToolRegistry, ToolResult


def _schema(name, props):
    return {
        "type": "function",
        "function": {"name": name, "parameters": {"type": "object", "properties": props}},
    }


def test_arg_summary_picks_named_key():
    assert _arg_summary("run_command", {"command": "git status"}) == "git status"
    assert _arg_summary("read_file", {"path": "a/b.py"}) == "a/b.py"
    assert _arg_summary("web_search", {"query": "kuzgun ai"}) == "kuzgun ai"
    assert _arg_summary("security_scan", {"target": "https://x"}) == "https://x"


def test_arg_summary_named_key_wins_over_bulky_content():
    # write_file: yol gösterilir, dev 'content' değil.
    out = _arg_summary("write_file", {"path": "f.py", "content": "x" * 5000})
    assert out == "f.py"


def test_arg_summary_flattens_newlines_and_truncates():
    s = _arg_summary("run_command", {"command": "a\nb\nc"})
    assert "\n" not in s
    long = _arg_summary("run_command", {"command": "z" * 100})
    assert len(long) <= 61 and long.endswith("…")


def test_arg_summary_fallback_first_value_or_empty():
    assert _arg_summary("bilinmeyen", {"x": "değer"}) == "değer"
    assert _arg_summary("bilinmeyen", {}) == ""


def test_tool_activity_has_label_and_arg():
    a = _tool_activity("run_command", {"command": "ls"})
    assert "komut" in a and "ls" in a
    # argümansız araçta yalnız etiket
    assert _tool_activity("web_search", {}) == _tool_activity("web_search", {})


def test_result_summary_marks_ok_and_error():
    assert _result_summary(ToolResult("tamam", ok=True)).startswith("✓")
    assert _result_summary(ToolResult("Error: patladı", ok=False)).startswith("✗")


def test_result_summary_counts_lines():
    out = _result_summary(ToolResult("bir\niki\nüç", ok=True))
    assert "satır" in out


def test_result_summary_appends_duration():
    assert "sn" in _result_summary(ToolResult("ok", ok=True), seconds=2.34)
    # çok kısa süre gösterilmez (gürültü olmasın)
    assert "sn" not in _result_summary(ToolResult("ok", ok=True), seconds=0.01)


def test_oneline_takes_first_nonblank():
    assert _oneline("\n\n  merhaba \ndünya") == "merhaba"


def test_run_turn_emits_tool_then_result_events():
    reg = ToolRegistry()
    reg.register(_schema("ping", {}), lambda: "pong")
    client = FakeModelClient(
        [
            AssistantMessage(text=None, tool_calls=[ToolCall(id="1", name="ping", arguments={})]),
            AssistantMessage(text="bitti"),
        ]
    )
    events: list[tuple[str | None, str]] = []
    out = run_turn(
        client,
        [{"role": "user", "content": "x"}],
        reg,
        mode="otonom",
        on_step=lambda m, kind=None: events.append((kind, m)),
    )
    assert out == "bitti"
    kinds = [k for k, _ in events]
    # önce araç, hemen ardından sonucu
    assert kinds.index("tool") < kinds.index("result")
    tool_msg = next(m for k, m in events if k == "tool")
    assert "ping" in tool_msg
    result_msg = next(m for k, m in events if k == "result")
    assert result_msg.startswith("✓")


def test_run_turn_blocked_tool_shows_stop_marker():
    # normal modda değişiklik yapan araç onaysız reddedilir → '⛔' sonucu.
    reg = ToolRegistry()
    reg.register(_schema("yaz", {}), lambda: "oldu", mutating=True)
    client = FakeModelClient(
        [
            AssistantMessage(text=None, tool_calls=[ToolCall(id="1", name="yaz", arguments={})]),
            AssistantMessage(text="tamam"),
        ]
    )
    events: list[tuple[str | None, str]] = []
    run_turn(
        client,
        [{"role": "user", "content": "x"}],
        reg,
        mode="normal",
        confirm=lambda name, args: False,  # onay verilmedi
        on_step=lambda m, kind=None: events.append((kind, m)),
    )
    result_msg = next(m for k, m in events if k == "result")
    assert result_msg.startswith("⛔")
