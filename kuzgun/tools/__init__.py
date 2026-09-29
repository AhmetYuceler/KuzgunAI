from __future__ import annotations

from collections.abc import Callable


class ToolResult(str):
    """Araç çalıştırma sonucu. `str` gibi davranır (geriye dönük uyum: geçmişe
    doğrudan yazılır, karşılaştırılır) ama bir `ok` bayrağı taşır.

    Böylece ajan döngüsü hatayı METNE bakarak ('Error:' önekiyle) değil, açık
    bayrakla anlar (B5): çıktısı gerçekten 'Error: 404' olan MEŞRU bir araç sonucu
    yanlışlıkla hata sayılıp devretmeyi tetiklemez."""

    ok: bool

    def __new__(cls, text: str, ok: bool = True) -> ToolResult:
        obj = super().__new__(cls, text)
        obj.ok = ok
        return obj


def _allowed_keys(schema: dict) -> set[str] | None:
    """Şemadaki izinli parametre adları. Doğrulama atlanır (None döner) eğer:
    - `properties` tanımlı değilse (serbest şema), ya da
    - `additionalProperties` açıkça True ise (şema fazladan anahtara izin veriyor).
    İkisi de MCP gibi serbest şemalarla geriye dönük uyum içindir."""
    params = schema.get("function", {}).get("parameters", {})
    if "properties" not in params or params.get("additionalProperties") is True:
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

    def execute(self, name: str, arguments: dict) -> ToolResult:
        if name not in self._tools:
            return ToolResult(f"Error: unknown tool {name}", ok=False)
        schema, fn, _ = self._tools[name]
        # Sözleşme doğrulaması: model yalnız şemada TANIMLI parametreleri geçebilir.
        # Gizli/dahili parametreler (ör. `_path`) şemada olmadığı için reddedilir.
        allowed = _allowed_keys(schema)
        if allowed is not None:
            extra = set(arguments) - allowed
            if extra:
                return ToolResult(
                    f"Error: bilinmeyen parametre(ler): {', '.join(sorted(extra))}", ok=False
                )
        try:
            result = fn(**arguments)
        except Exception as exc:  # bozuk argüman, çalışma hatası vb.
            return ToolResult(f"Error: {exc}", ok=False)
        return ToolResult(str(result), ok=True)
