from __future__ import annotations

import json

from kuzgun.models import AssistantMessage, ToolCall
from kuzgun.permissions import is_allowed
from kuzgun.tools import ToolRegistry


def _first_json_object(text: str) -> str | None:
    """Metindeki ilk DENGELİ {...} nesnesini döndürür (fazla kapanış parantezi tolere)."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def extract_tool_calls_from_text(text: str | None) -> list[ToolCall]:
    """Model, araç çağrısını gerçek çağrı yerine metin-JSON olarak verirse yakalar.

    Örn: '```json {"name":"write_file","arguments":{...}}```' → ToolCall.
    Küçük modellerin sık yaptığı format hatasını telafi eder.
    """
    if not text:
        return []
    blob = _first_json_object(text)
    if not blob:
        return []
    try:
        data = json.loads(blob)
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    name = data.get("name") or data.get("tool")
    args = data.get("arguments")
    if args is None:
        args = data.get("parameters", {})
    if name and isinstance(args, dict):
        return [ToolCall(id="text-1", name=str(name), arguments=args)]
    return []


def _assistant_to_history(msg: AssistantMessage) -> dict:
    entry: dict = {"role": "assistant", "content": msg.text or ""}
    if msg.tool_calls:
        entry["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
            }
            for tc in msg.tool_calls
        ]
    return entry


def _last_user_text(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def run_turn(
    client,
    messages: list[dict],
    registry: ToolRegistry,
    mode: str = "normal",
    confirm=None,
    max_steps: int = 10,
    escalate=None,
) -> str:
    """Ajan döngüsü. `escalate` verilirse, model döngüye girer / araçlar üst üste
    hata verir / max_steps aşılırsa otomatik olarak uzmana (Claude) devreder."""
    last_sig = None
    repeat = 0
    err_streak = 0
    for _ in range(max_steps):
        assistant = client.chat(messages, registry.schemas())
        # Model tool call'u metin-JSON olarak verdiyse gerçek çağrıya çevir.
        if not assistant.tool_calls:
            recovered = extract_tool_calls_from_text(assistant.text)
            if recovered:
                assistant.tool_calls = recovered
                assistant.text = None
        messages.append(_assistant_to_history(assistant))
        if not assistant.tool_calls:
            return assistant.text or ""
        # Döngü tespiti: aynı araç çağrısı imzası art arda tekrar ediyor mu?
        sig = tuple(
            (tc.name, json.dumps(tc.arguments, sort_keys=True))
            for tc in assistant.tool_calls
        )
        repeat = repeat + 1 if sig == last_sig else 0
        last_sig = sig
        step_error = False
        for tc in assistant.tool_calls:
            mutating = registry.is_mutating(tc.name)
            allowed, reason = is_allowed(tc.name, tc.arguments, mutating, mode, confirm)
            result = registry.execute(tc.name, tc.arguments) if allowed else reason
            if isinstance(result, str) and result.startswith("Error:"):
                step_error = True
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": result}
            )
        err_streak = err_streak + 1 if step_error else 0
        # Devir tetikleyicileri: döngü ya da üst üste araç hatası.
        if escalate is not None and (repeat >= 2 or err_streak >= 2):
            return escalate(_last_user_text(messages))
    # max_steps aşıldı: escalate varsa devret, yoksa hata ver.
    if escalate is not None:
        return escalate(_last_user_text(messages))
    raise RuntimeError(f"max_steps ({max_steps}) aşıldı; model döngüde kaldı.")
