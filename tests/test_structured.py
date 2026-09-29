"""Yapılandırılmış (JSON) model çıktısı + yeniden deneme (Faz C1)."""

from __future__ import annotations

from kuzgun.models import AssistantMessage, FakeModelClient
from kuzgun.structured import complete_json


def test_parses_valid_json_list():
    client = FakeModelClient([AssistantMessage(text='["ilk", "ikinci"]', tool_calls=[])])
    out = complete_json(client, [{"role": "user", "content": "plan"}])
    assert out == ["ilk", "ikinci"]


def test_parses_json_object_from_noisy_text():
    client = FakeModelClient([
        AssistantMessage(text='İşte plan: {"adimlar": ["a", "b"]} umarım olur', tool_calls=[]),
    ])
    out = complete_json(client, [{"role": "user", "content": "plan"}])
    assert out == {"adimlar": ["a", "b"]}


def test_retries_on_invalid_then_succeeds():
    client = FakeModelClient([
        AssistantMessage(text="hiç json yok burada", tool_calls=[]),
        AssistantMessage(text='{"ok": true}', tool_calls=[]),
    ])
    out = complete_json(client, [{"role": "user", "content": "?"}], retries=3)
    assert out == {"ok": True}


def test_returns_default_after_exhausting_retries():
    client = FakeModelClient([AssistantMessage(text="json değil", tool_calls=[])] * 5)
    out = complete_json(client, [{"role": "user", "content": "?"}], retries=2, default=[])
    assert out == []


def test_validate_callback_rejects_then_retries():
    client = FakeModelClient([
        AssistantMessage(text='{"tip": "yanlis"}', tool_calls=[]),
        AssistantMessage(text='{"tip": "liste", "ogeler": [1, 2]}', tool_calls=[]),
    ])
    out = complete_json(
        client,
        [{"role": "user", "content": "?"}],
        retries=3,
        validate=lambda d: isinstance(d, dict) and "ogeler" in d,
    )
    assert out["ogeler"] == [1, 2]
