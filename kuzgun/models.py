from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class AssistantMessage:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


@runtime_checkable
class ModelClient(Protocol):
    """Bir dil modeli istemcisinin sözleşmesi: mesaj+araç al, AssistantMessage döndür.

    OllamaClient (gerçek) ve FakeModelClient (test) bu şekli sağlar; ileride
    Claude/vLLM istemcileri de aynı sözleşmeye uyar.
    """

    def chat(self, messages, tools) -> "AssistantMessage": ...


def _parse_arguments(raw: str | None) -> dict:
    """Model'in ürettiği araç argümanı JSON'unu güvenle sözlüğe çevirir.

    Küçük modeller bazen bozuk/eksik JSON üretir; böyle bir durumda tur
    çökmesin diye boş sözlük döneriz (ToolRegistry eksik argümanı zaten
    'Error: ...' olarak modele geri bildirir).
    """
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


class FakeModelClient:
    """Testler için: önceden yazılmış mesajları sırayla döndürür."""

    def __init__(self, scripted: list[AssistantMessage]):
        self._scripted = list(scripted)
        self._i = 0

    def chat(self, messages, tools) -> AssistantMessage:
        msg = self._scripted[self._i]
        self._i += 1
        return msg


class OllamaClient:
    """Ollama'nın OpenAI-uyumlu API'sine bağlanır."""

    def __init__(
        self,
        model: str = "qwen2.5:7b-instruct",
        base_url: str = "http://localhost:11434/v1",
    ):
        from openai import OpenAI

        self._client = OpenAI(base_url=base_url, api_key="ollama")
        self._model = model

    def chat(self, messages, tools) -> AssistantMessage:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools or None,
            temperature=0.2,
        )
        m = resp.choices[0].message
        tool_calls = []
        for tc in (m.tool_calls or []):
            tool_calls.append(
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=_parse_arguments(tc.function.arguments),
                )
            )
        return AssistantMessage(text=m.content, tool_calls=tool_calls)
