from __future__ import annotations

import json

from kuzgun.models import AssistantMessage
from kuzgun.permissions import is_allowed
from kuzgun.tools import ToolRegistry


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
