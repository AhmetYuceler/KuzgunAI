from __future__ import annotations

from pathlib import Path


def load_notes(path: str) -> str:
    """Kalıcı not dosyasını (KUZGUN.md) okur; yoksa boş string döner."""
    p = Path(path)
    if not p.is_file():
        return ""
    try:
        return p.read_text(encoding="utf-8").strip()
    except Exception:  # noqa: BLE001
        return ""


def add_note(path: str, fact: str) -> str:
    """Kalıcı not dosyasına bir bilgi ekler (madde olarak)."""
    fact = (fact or "").strip().replace("\n", " ")
    if not fact:
        return "Error: boş not."
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(f"- {fact}\n")
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"
    return f"Hatırlandı: {fact}"
