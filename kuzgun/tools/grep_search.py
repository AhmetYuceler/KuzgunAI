from __future__ import annotations

import re
from pathlib import Path

from kuzgun.tools._paths import is_ignored

GREP_SCHEMA = {
    "type": "function",
    "function": {
        "name": "grep_search",
        "description": (
            "Dosyaların içinde bir düzenli ifade (regex) arar. Eşleşen satırları "
            "'dosya:satır: içerik' biçiminde döndürür. Kod/metin içinde bir şey "
            "aramak için kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Aranacak regex."},
                "root": {"type": "string", "description": "Başlangıç klasörü. Varsayılan '.'."},
                "glob": {"type": "string", "description": "Dosya deseni. Varsayılan '**/*'."},
            },
            "required": ["pattern"],
        },
    },
}


def grep_search(pattern: str, root: str = ".", glob: str = "**/*") -> str:
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        return f"Error: geçersiz regex: {exc}"
    results = []
    for path in Path(root).glob(glob):
        if not path.is_file() or is_ignored(path):
            continue
        try:
            for i, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                if rx.search(line):
                    results.append(f"{path}:{i}: {line.strip()}")
        except Exception:
            continue
        if len(results) >= 200:
            break
    return "\n".join(results) if results else "Eşleşme yok."
