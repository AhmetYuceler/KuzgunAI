"""Oturum arşivi — Claude Code'un /resume'ü gibi.

Her `kuzgun` oturumunun konuşması her turdan sonra diske yazılır
(`data/sessions/<id>.json`); sonra `/resume` (liste + seçim), `/resume <ad|id>`,
`kuzgun --continue` (en son) ya da `kuzgun --resume <ad>` ile geri yüklenir.
Claude Code gibi proje bazlı değil, tek arşiv; `cwd` metaveride tutulur.
Eski oturumlar (varsayılan 30 gün) açılışta silinir.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid

_TITLE_MAX = 60


def title_for(messages: list[dict]) -> str:
    """İlk kullanıcı mesajından kısa başlık (Claude Code'un otomatik başlığı gibi)."""
    for m in messages:
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            text = re.sub(r"\[ekli resim:[^\]]*\]", "", m["content"]).strip()
            text = " ".join(text.split())
            if len(text) > _TITLE_MAX:
                return text[: _TITLE_MAX - 3] + "..."
            return text or "(boş)"
    return "(boş)"


class SessionArchive:
    def __init__(self, directory: str = "data/sessions"):
        self.dir = directory
        os.makedirs(self.dir, exist_ok=True)

    @staticmethod
    def new_id() -> str:
        return time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]

    def path(self, sid: str) -> str:
        return os.path.join(self.dir, f"{sid}.json")

    def save(self, sid: str, messages: list[dict], mode: str = "normal", cwd: str = "") -> None:
        """Konuşmayı (tam mesaj listesi) ve metaveriyi yazar; ad korunur."""
        name = ""
        created = time.time()
        if os.path.exists(self.path(sid)):
            try:
                old = self._read(sid)
                name = old.get("name", "")
                created = old.get("created", created)
            except (OSError, ValueError):
                pass
        data = {
            "id": sid,
            "name": name,
            "title": title_for(messages),
            "created": created,
            "updated": time.time(),
            "cwd": cwd,
            "mode": mode,
            "turns": sum(1 for m in messages if m.get("role") == "user"),
            "messages": messages,
        }
        tmp = self.path(sid) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, self.path(sid))  # atomik: yarım dosya kalmasın

    def _read(self, sid: str) -> dict:
        with open(self.path(sid), encoding="utf-8") as f:
            return json.load(f)

    def load(self, sid: str) -> tuple[list[dict], dict]:
        data = self._read(sid)
        messages = data.pop("messages", [])
        return messages, data

    @staticmethod
    def _same_dir(a: str, b: str) -> bool:
        norm = lambda p: os.path.normcase(os.path.normpath(p))  # noqa: E731
        return norm(a) == norm(b)

    def list(self, limit: int = 15, cwd: str | None = None) -> list[dict]:
        """Metaveriler, en yeni önce; kullanıcı mesajı olmayan (boş) oturumlar atlanır.
        `cwd` verilirse yalnız o klasörde açılmış oturumlar (Claude Code proje bazlı)."""
        metas = []
        for fn in os.listdir(self.dir):
            if not fn.endswith(".json"):
                continue
            try:
                d = self._read(fn[:-5])
            except (OSError, ValueError):
                continue
            if d.get("turns", 0) == 0:
                continue
            if cwd is not None and not self._same_dir(d.get("cwd", ""), cwd):
                continue
            d.pop("messages", None)
            metas.append(d)
        metas.sort(key=lambda d: d.get("updated", 0), reverse=True)
        return metas[:limit]

    def latest(self, cwd: str | None = None) -> dict | None:
        lst = self.list(limit=1, cwd=cwd)
        return lst[0] if lst else None

    def find(self, key: str) -> dict | None:
        """Ad ya da id ile bul (id için ön ek yeterli)."""
        for d in self.list(limit=10_000):
            if key and (d.get("name") == key or d["id"] == key or d["id"].startswith(key)):
                return d
        return None

    def rename(self, sid: str, name: str) -> None:
        d = self._read(sid)
        d["name"] = name.strip()
        tmp = self.path(sid) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, self.path(sid))

    def sweep(self, days: int = 30) -> None:
        """days günden eski oturum dosyalarını siler (Claude Code cleanupPeriodDays gibi)."""
        cutoff = time.time() - days * 86400
        for fn in os.listdir(self.dir):
            p = os.path.join(self.dir, fn)
            try:
                if fn.endswith(".json") and os.path.getmtime(p) < cutoff:
                    os.remove(p)
            except OSError:
                pass
