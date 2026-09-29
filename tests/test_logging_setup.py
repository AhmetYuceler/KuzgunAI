"""Loglama altyapısı (Faz B1)."""

from __future__ import annotations

import logging

from kuzgun.logging_setup import get_logger, setup_logging, timed


def test_get_logger_is_under_kuzgun_namespace():
    log = get_logger("mcp")
    assert log.name == "kuzgun.mcp"
    assert get_logger().name == "kuzgun"


def test_setup_logging_is_idempotent():
    root = logging.getLogger("kuzgun")
    setup_logging(level="INFO")
    n = len(root.handlers)
    setup_logging(level="INFO")
    assert len(root.handlers) == n  # ikinci çağrı handler eklemez


def test_timed_logs_duration(caplog):
    log = get_logger("test")
    with caplog.at_level(logging.INFO, logger="kuzgun.test"):
        with timed(log, "isim", extra="x"):
            pass
    msgs = [r.getMessage() for r in caplog.records]
    assert any("isim" in m and "ms" in m for m in msgs)


def test_run_turn_logs_model_and_tool(caplog):
    from kuzgun.models import AssistantMessage, FakeModelClient, ToolCall
    from kuzgun.agent import run_turn
    from kuzgun.tools import ToolRegistry

    reg = ToolRegistry()
    reg.register(
        {"type": "function", "function": {"name": "echo",
         "parameters": {"type": "object", "properties": {"text": {"type": "string"}}}}},
        lambda text="": f"e:{text}",
    )
    client = FakeModelClient([
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "echo", {"text": "x"})]),
        AssistantMessage(text="bitti", tool_calls=[]),
    ])
    with caplog.at_level(logging.INFO, logger="kuzgun.agent"):
        out = run_turn(client, [{"role": "user", "content": "?"}], reg)
    assert out == "bitti"
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "echo" in text  # araç çalıştırması loglandı
