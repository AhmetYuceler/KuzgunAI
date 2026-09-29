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

    def chat(self, messages, tools) -> AssistantMessage: ...


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


class OpenAICompatBackend:
    """OpenAI-uyumlu bir sohbet API'sine bağlanır (Ollama, vLLM, Claude-proxy…).

    Ollama varsayılan; `base_url`/`api_key`/`model` değiştirerek başka bir arka uca
    (ör. GPU sunucusundaki vLLM) taşınır — motor kodu değişmeden (B3/Faz D)."""

    def __init__(
        self,
        model: str = "qwen2.5:7b-instruct",
        base_url: str = "http://localhost:11434/v1",
        timeout: float = 300,
        api_key: str = "ollama",
        temperature: float = 0.2,
        max_tokens: int | None = None,
        max_retries: int = 1,
    ):
        from openai import OpenAI

        # timeout: arka uç takılırsa sonsuza dek beklenmesin (Ctrl+C'siz kurtulma).
        self.client_timeout = timeout
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client = OpenAI(
            base_url=base_url, api_key=api_key, timeout=timeout, max_retries=max_retries
        )
        self._model = model

    def chat(self, messages, tools) -> AssistantMessage:
        kwargs = {}
        if self._max_tokens:
            kwargs["max_tokens"] = self._max_tokens
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools or None,
            temperature=self._temperature,
            **kwargs,
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


# Eski ad, geriye dönük uyum için takma ad olarak korunur.
OllamaClient = OpenAICompatBackend


class FallbackClient:
    """Birden çok model arka ucunu sırayla dener (C4): biri hata/zaman aşımı verirse
    sonrakine geçer. Hepsi düşerse son hatayı yeniden fırlatır. Böylece birincil
    model yoğun/erişilemezken Kuzgun ikincil bir modelle çalışmaya devam eder."""

    def __init__(self, clients: list):
        if not clients:
            raise ValueError("FallbackClient en az bir istemci gerektirir")
        self._clients = list(clients)

    def chat(self, messages, tools) -> AssistantMessage:
        import logging

        last_exc: Exception | None = None
        for i, c in enumerate(self._clients):
            try:
                return c.chat(messages, tools)
            except Exception as exc:  # noqa: BLE001 — sonraki arka uca geç
                last_exc = exc
                logging.getLogger("kuzgun.models").warning(
                    "model arka ucu %d/%d düştü (%s); sonrakine geçiliyor",
                    i + 1, len(self._clients), exc,
                )
        raise last_exc  # type: ignore[misc]
