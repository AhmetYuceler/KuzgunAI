from __future__ import annotations

from typing import Callable


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, tuple[dict, Callable]] = {}

    def register(self, schema: dict, fn: Callable) -> None:
        name = schema["function"]["name"]
        self._tools[name] = (schema, fn)

    def schemas(self) -> list[dict]:
        return [schema for schema, _ in self._tools.values()]

    def execute(self, name: str, arguments: dict) -> str:
        if name not in self._tools:
            return f"Error: unknown tool {name}"
        _, fn = self._tools[name]
        try:
            result = fn(**arguments)
        except Exception as exc:  # bozuk argüman, çalışma hatası vb.
            return f"Error: {exc}"
        return str(result)
