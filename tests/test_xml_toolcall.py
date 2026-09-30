"""Qwen3-Coder XML araç-çağrısı kurtarma + araç çıktısı bütçesi + döngü kırıcı.

Gerçek gözlem (80B Qwen3-Coder-Next): model araç çağrısını gerçek tool_call yerine
metin olarak '<tool_call><function=read_file><parameter=path>...' biçiminde yazdı;
ayrıştırılmadığı için Kuzgun bunu cevap sanıp turu bitirdi ('taramayı durdurdu').
Ayrıca 751 satırlık dosyayı 5 kez üst üste okudu (çıktı 4000'e kırpılıp tam metni
alamadığı için). Bu testler üç düzeltmeyi de doğrular.
"""

from __future__ import annotations

from kuzgun.agent import (
    _render_result,
    _xml_tool_calls,
    extract_tool_calls_from_text,
    run_turn,
)
from kuzgun.models import AssistantMessage, FakeModelClient, ToolCall
from kuzgun.tools import ToolRegistry


def _schema(name, props):
    return {
        "type": "function",
        "function": {"name": name, "parameters": {"type": "object", "properties": props}},
    }


# ---- XML ayrıştırma --------------------------------------------------------


def test_xml_single_call_coerces_int():
    xml = (
        "<tool_call>\n<function=read_file>\n<parameter=path>\n"
        "C:\\a\\b.py\n<parameter=max_bytes>\n100000000\n</tool_call>"
    )
    calls = _xml_tool_calls(xml)
    assert len(calls) == 1
    assert calls[0].name == "read_file"
    assert calls[0].arguments["path"] == "C:\\a\\b.py"
    assert calls[0].arguments["max_bytes"] == 100000000  # int'e çevrildi


def test_xml_tolerates_missing_close_tags():
    # Model </parameter>/</function> yazmasa bile ayrıştırılmalı.
    xml = "<function=web_search>\n<parameter=query>\nkuzgun ai\n</tool_call>"
    calls = _xml_tool_calls(xml)
    assert calls[0].name == "web_search"
    assert calls[0].arguments["query"] == "kuzgun ai"


def test_xml_multiple_calls():
    xml = (
        "<tool_call><function=read_file><parameter=path>/x</parameter></function></tool_call>"
        "<tool_call><function=read_file><parameter=path>/y</parameter></function></tool_call>"
    )
    calls = _xml_tool_calls(xml)
    assert [c.arguments["path"] for c in calls] == ["/x", "/y"]


def test_xml_ignored_in_plain_text():
    assert _xml_tool_calls("normal bir cevap, araç yok") == []


def test_extract_routes_xml():
    xml = "<tool_call><function=read_file><parameter=path>/a</parameter></function></tool_call>"
    calls = extract_tool_calls_from_text("Şunu okuyacağım:\n" + xml)
    assert calls and calls[0].name == "read_file" and calls[0].arguments["path"] == "/a"


# ---- run_turn XML kurtarma (uçtan uca) -------------------------------------


def test_run_turn_recovers_xml_and_continues():
    reg = ToolRegistry()
    reg.register(
        _schema("read_file", {"path": {"type": "string"}, "max_bytes": {"type": "integer"}}),
        lambda path, max_bytes=100000: f"icerik:{path}:{max_bytes}",
    )
    xml = (
        "DÜŞÜN: dosyayı okuyacağım.\n<tool_call>\n<function=read_file>\n"
        "<parameter=path>\n/a/b.py\n<parameter=max_bytes>\n100000000\n</tool_call>"
    )
    client = FakeModelClient([AssistantMessage(text=xml), AssistantMessage(text="tamam")])
    msgs = [{"role": "user", "content": "oku"}]
    out = run_turn(client, msgs, reg, mode="otonom")
    assert out == "tamam"
    tool_msgs = [m for m in msgs if m.get("role") == "tool"]
    assert tool_msgs and tool_msgs[0]["content"] == "icerik:/a/b.py:100000000"


# ---- araç çıktısı bütçesi --------------------------------------------------


def test_render_result_respects_budget():
    text = "a" * 5000
    assert _render_result(text, None, 10000) == text  # bütçe altında: aynen
    clipped = _render_result(text, None, 1000)  # bütçe üstü: kırpılır
    assert len(clipped) < len(text)


def test_run_turn_passes_budget_so_file_not_clipped():
    reg = ToolRegistry()
    big = "SATIR\n" * 700  # ~4200 karakter, eski 4000 bütçesini aşar
    reg.register(_schema("read_file", {"path": {"type": "string"}}), lambda path: big)
    client = FakeModelClient(
        [
            AssistantMessage(text=None, tool_calls=[ToolCall("1", "read_file", {"path": "/f"})]),
            AssistantMessage(text="ok"),
        ]
    )
    msgs = [{"role": "user", "content": "oku"}]
    run_turn(client, msgs, reg, mode="otonom", max_tool_chars=40000)
    tool_msg = next(m for m in msgs if m.get("role") == "tool")
    assert tool_msg["content"] == big  # 40000 bütçe → kırpılmadı


# ---- döngü kırıcı (uzman yok) ----------------------------------------------


def test_run_turn_breaks_repeat_loop_without_escalate():
    reg = ToolRegistry()
    reg.register(_schema("ping", {}), lambda: "pong")
    call = AssistantMessage(text=None, tool_calls=[ToolCall("1", "ping", {})])
    # 3 kez aynı çağrı, sonra cevap. escalate=None → çökmemeli, döngüyü kırmalı.
    client = FakeModelClient([call, call, call, AssistantMessage(text="bitti")])
    msgs = [{"role": "user", "content": "x"}]
    out = run_turn(client, msgs, reg, mode="otonom", max_steps=10)
    assert out == "bitti"
    assert any(
        m.get("role") == "system" and "tekrar" in m.get("content", "").lower() for m in msgs
    )
