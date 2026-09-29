from __future__ import annotations

from collections.abc import Callable


def _allowed_keys(schema: dict) -> set[str] | None:
    """Şemadaki izinli parametre adları. `properties` tanımlı değilse None
    (doğrulama atlanır — MCP gibi serbest şemalar için geriye dönük güvenli)."""
    params = schema.get("function", {}).get("parameters", {})
    if "properties" not in params:
        return None
    return set(params["properties"].keys())


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, tuple[dict, Callable, bool]] = {}

    def register(self, schema: dict, fn: Callable, mutating: bool = False) -> None:
        name = schema["function"]["name"]
        if name in self._tools:
            # İsim çakışması sessizce ezmesin (bir araç diğerini gölgeleyemez).
            raise ValueError(f"'{name}' adlı araç zaten kayıtlı (isim çakışması)")
        self._tools[name] = (schema, fn, mutating)

    def schemas(self) -> list[dict]:
        return [schema for schema, _, _ in self._tools.values()]

    def has(self, name: str) -> bool:
        return name in self._tools

    def is_mutating(self, name: str) -> bool:
        entry = self._tools.get(name)
        return bool(entry[2]) if entry else False

    def execute(self, name: str, arguments: dict) -> str:
        if name not in self._tools:
            return f"Error: unknown tool {name}"
        schema, fn, _ = self._tools[name]
        # Sözleşme doğrulaması: model yalnız şemada TANIMLI parametreleri geçebilir.
        # Gizli/dahili parametreler (ör. `_path`) şemada olmadığı için reddedilir.
        allowed = _allowed_keys(schema)
        if allowed is not None:
            extra = set(arguments) - allowed
            if extra:
                return f"Error: bilinmeyen parametre(ler): {', '.join(sorted(extra))}"
        try:
            result = fn(**arguments)
        except Exception as exc:  # bozuk argüman, çalışma hatası vb.
            return f"Error: {exc}"
        return str(result)
