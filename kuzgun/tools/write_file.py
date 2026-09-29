from __future__ import annotations

from pathlib import Path

WRITE_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": (
            "Bir dosyaya metin YAZAR (varsa üzerine yazar). Üst klasörler yoksa "
            "oluşturur. Kalıcı değişiklik yapar; dikkatli kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Yazılacak dosyanın yolu."},
                "content": {"type": "string", "description": "Dosyaya yazılacak metin."},
            },
            "required": ["path", "content"],
        },
    },
}


def write_file(path: str, content: str) -> str:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    except Exception as exc:
        return f"Error: {exc}"
    return f"Yazıldı: {path} ({len(content)} karakter)"
