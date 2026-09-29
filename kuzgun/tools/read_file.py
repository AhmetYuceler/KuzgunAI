from __future__ import annotations

from pathlib import Path

READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": (
            "Yerel dosya sisteminden bir dosyanın metnini okur. Bir dosyanın "
            "içeriğini görmek/incelemek gerektiğinde kullan. Mutlak yol ver. "
            "Kodu çalıştırmaz, sadece metni döndürür."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Okunacak dosyanın yolu."},
                "max_bytes": {
                    "type": "integer",
                    "description": "Okunacak azami karakter. Varsayılan 100000.",
                },
            },
            "required": ["path"],
        },
    },
}


def read_file(path: str, max_bytes: int = 100_000) -> str:
    p = Path(path)
    if not p.is_file():
        return f"Error: dosya bulunamadı: {path}"
    text = p.read_text(encoding="utf-8", errors="replace")
    return text[:max_bytes]
