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


def run_turn(
    client,
    messages: list[dict],
    registry: ToolRegistry,
    mode: str = "normal",
    confirm=None,
    max_steps: int = 10,
) -> str:
    for _ in range(max_steps):
        assistant = client.chat(messages, registry.schemas())
        messages.append(_assistant_to_history(assistant))
        if not assistant.tool_calls:
            return assistant.text or ""
        for tc in assistant.tool_calls:
            mutating = registry.is_mutating(tc.name)
            allowed, reason = is_allowed(tc.name, tc.arguments, mutating, mode, confirm)
            result = registry.execute(tc.name, tc.arguments) if allowed else reason
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": result}
            )
    raise RuntimeError(f"max_steps ({max_steps}) aşıldı; model döngüde kaldı.")
