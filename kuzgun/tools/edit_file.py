from __future__ import annotations

import difflib
from pathlib import Path

EDIT_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": (
            "Bir dosyada HEDEFLİ değişiklik yapar: old_string'i new_string ile "
            "değiştirir (tüm dosyayı yeniden yazmadan). Kod düzenlemek için tercih et. "
            "old_string dosyada TEK bir yerde eşleşmeli (yoksa daha çok bağlam ekle) "
            "ya da replace_all=true ver. Değişiklik özetini (diff) döndürür."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Düzenlenecek dosyanın yolu."},
                "old_string": {"type": "string", "description": "Değiştirilecek MEVCUT metin (birebir)."},
                "new_string": {"type": "string", "description": "Yerine yazılacak YENİ metin."},
                "replace_all": {
                    "type": "boolean",
                    "description": "Tüm eşleşmeleri değiştir (varsayılan false: tek eşleşme).",
                },
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
}


def _diff(old: str, new: str, path: str) -> str:
    """Birleşik (unified) diff — kullanıcı ve model neyin değiştiğini görsün."""
    lines = list(
        difflib.unified_diff(
            old.splitlines(), new.splitlines(),
            fromfile=path, tofile=path, lineterm="", n=2,
        )
    )
    return "\n".join(lines)


def edit_file(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    try:
        p = Path(path)
        if not p.is_file():
            return f"Error: dosya bulunamadı: {path}"
        original = p.read_text(encoding="utf-8", errors="replace")
        if old_string == new_string:
            return "Error: old_string ile new_string aynı; değişiklik yok."
        count = original.count(old_string)
        if count == 0:
            return (
                f"Error: old_string dosyada bulunamadı: {path}. "
                "Metni birebir (boşluk/girinti dahil) ver; önce read_file ile bak."
            )
        if count > 1 and not replace_all:
            return (
                f"Error: old_string {count} yerde eşleşiyor. Daha çok bağlam ekleyip "
                "TEKİL yap ya da replace_all=true ver."
            )
        updated = original.replace(old_string, new_string)
        p.write_text(updated, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"
    n = count if replace_all else 1
    diff = _diff(original, updated, path)
    return f"Düzenlendi: {path} ({n} değişiklik)\n{diff}"
