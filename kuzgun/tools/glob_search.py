from __future__ import annotations

from pathlib import Path

from kuzgun.tools._paths import is_ignored

GLOB_SCHEMA = {
    "type": "function",
    "function": {
        "name": "glob_search",
        "description": (
            "Bir desenle (glob) eşleşen dosyaları bulur. Örn desen: '*.py' veya "
            "'**/*.txt'. Bir klasörde hangi dosyalar var öğrenmek için kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob deseni, örn '**/*.py'."},
                "root": {"type": "string", "description": "Başlangıç klasörü. Varsayılan '.'."},
            },
            "required": ["pattern"],
        },
    },
}


def glob_search(pattern: str, root: str = ".") -> str:
    try:
        matches = sorted(
            str(p) for p in Path(root).glob(pattern) if not is_ignored(p)
        )
    except Exception as exc:
        return f"Error: {exc}"
    if not matches:
        return "Eşleşme yok."
    return "\n".join(matches)
