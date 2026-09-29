"""Yedek model zinciri: bir arka uç düşerse sıradakine geç (Faz C4)."""

from __future__ import annotations

import pytest

from kuzgun.models import AssistantMessage, FallbackClient


class _Raises:
    def __init__(self, exc):
        self.exc = exc
        self.calls = 0

    def chat(self, messages, tools):
        self.calls += 1
        raise self.exc


class _Ok:
    def __init__(self, text):
        self.text = text
        self.calls = 0

    def chat(self, messages, tools):
        self.calls += 1
        return AssistantMessage(text=self.text, tool_calls=[])


def test_uses_first_that_succeeds():
    a, b = _Ok("birinci"), _Ok("ikinci")
    fb = FallbackClient([a, b])
    assert fb.chat([], []).text == "birinci"
    assert b.calls == 0  # ilk başardı → ikinci hiç çağrılmadı


def test_falls_back_on_error():
    a, b = _Raises(RuntimeError("ollama düştü")), _Ok("yedek")
    fb = FallbackClient([a, b])
    assert fb.chat([], []).text == "yedek"
    assert a.calls == 1 and b.calls == 1


def test_raises_when_all_fail():
    a, b = _Raises(RuntimeError("x")), _Raises(TimeoutError("y"))
    fb = FallbackClient([a, b])
    with pytest.raises(Exception):
        fb.chat([], [])


def test_empty_chain_raises():
    with pytest.raises(ValueError):
        FallbackClient([])
