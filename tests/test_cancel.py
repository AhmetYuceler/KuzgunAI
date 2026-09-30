"""İş iptali: kullanıcı ESC/Ctrl+C basınca çalışan ajan turu ADIMLAR ARASINDA
durmalı (tüm max_steps bitene kadar beklemeden). run_turn `cancel` geri çağrısı
her adımın başında kontrol edilir; True dönerse '[iptal edildi]' ile çıkılır.
"""

from __future__ import annotations

from kuzgun.agent import CANCELLED, run_turn
from kuzgun.models import AssistantMessage, FakeModelClient, ToolCall
from kuzgun.tools import ToolRegistry


def _schema(name, props):
    return {
        "type": "function",
        "function": {"name": name, "parameters": {"type": "object", "properties": props}},
    }


def test_cancel_before_first_model_call():
    reg = ToolRegistry()
    reg.register(_schema("ping", {}), lambda: "pong")
    # cancel hemen True → model hiç çağrılmamalı (script boş bırakılabilir).
    client = FakeModelClient([AssistantMessage(text="olmamali")])
    out = run_turn(client, [{"role": "user", "content": "x"}], reg, cancel=lambda: True)
    assert out == CANCELLED


def test_cancel_after_one_step():
    reg = ToolRegistry()
    reg.register(_schema("ping", {}), lambda: "pong")
    ping = AssistantMessage(text=None, tool_calls=[ToolCall("1", "ping", {})])
    client = FakeModelClient([ping, ping, ping, AssistantMessage(text="son")])
    n = {"i": 0}

    def cancel():
        n["i"] += 1
        return n["i"] > 1  # 1. adım geçer, 2. adımın başında iptal

    out = run_turn(client, [{"role": "user", "content": "x"}], reg, mode="otonom", cancel=cancel)
    assert out == CANCELLED


def test_no_cancel_runs_normally():
    reg = ToolRegistry()
    reg.register(_schema("ping", {}), lambda: "pong")
    client = FakeModelClient(
        [
            AssistantMessage(text=None, tool_calls=[ToolCall("1", "ping", {})]),
            AssistantMessage(text="bitti"),
        ]
    )
    out = run_turn(client, [{"role": "user", "content": "x"}], reg, cancel=lambda: False)
    assert out == "bitti"
