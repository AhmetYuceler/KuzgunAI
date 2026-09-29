from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Protocol, runtime_checkable

from kuzgun.embeddings import cosine

log = logging.getLogger("kuzgun.memory")


@runtime_checkable
class MemoryStore(Protocol):
    """Hafıza deposunun sözleşmesi (Memory ve ileride başka arka uçlar sağlar)."""

    def add(self, user_text: str, assistant_text: str, embedder) -> None: ...
    def search(self, query: str, embedder, k: int = 3, min_score: float = 0.0) -> list[dict]: ...
    def count(self) -> int: ...


def _embedder_id(embedder) -> str:
    """Embedder'ın model kimliği (kayıtta hangi modelle üretildiğini tutmak için)."""
    return str(
        getattr(embedder, "model", None)
        or getattr(embedder, "_model", None)
        or type(embedder).__name__
    )


class Memory:
    """Konuşmaları SQLite'ta embedding ile saklayan, benzerlikle arayan hafıza.

    Sınırsız büyür; taşınabilir tek dosyadır (db_path). ':memory:' geçici bellek.
    Thread-güvenlidir: tek bağlantı (check_same_thread=False) + kilit ile korunur,
    böylece FastAPI sunucusunun iş parçacıklarından da güvenle kullanılır.

    Her kayıt hangi embedding modeliyle ve kaç boyutla üretildiğini saklar; arama
    sırasında SORGUDAN farklı boyutlu kayıtlar atlanır (model değişince eski
    vektörler sessizce çöp benzerlik üretmesin — B7).
    """

    def __init__(self, db_path: str = "data/memory.db"):
        self._db_path = str(db_path)
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS memories ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, "
                "user TEXT, assistant TEXT, embedding TEXT, "
                "emb_model TEXT, dim INTEGER)"
            )
            self._migrate()
            self._conn.commit()

    def _migrate(self) -> None:
        """Eski şemaya (emb_model/dim sütunları olmayan) sahip DB'leri yükseltir."""
        cols = {r[1] for r in self._conn.execute("PRAGMA table_info(memories)")}
        if "emb_model" not in cols:
            self._conn.execute("ALTER TABLE memories ADD COLUMN emb_model TEXT")
        if "dim" not in cols:
            self._conn.execute("ALTER TABLE memories ADD COLUMN dim INTEGER")

    def add(self, user_text: str, assistant_text: str, embedder) -> None:
        emb = embedder.embed(f"{user_text}\n{assistant_text}")  # ağ çağrısı: kilit dışında
        payload = json.dumps(emb)
        model = _embedder_id(embedder)
        dim = len(emb)
        with self._lock:
            self._conn.execute(
                "INSERT INTO memories (ts, user, assistant, embedding, emb_model, dim) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (time.time(), user_text, assistant_text, payload, model, dim),
            )
            self._conn.commit()

    def search(self, query: str, embedder, k: int = 3, min_score: float = 0.0) -> list[dict]:
        q = embedder.embed(query)  # ağ çağrısı: kilit dışında
        qdim = len(q)
        with self._lock:
            rows = self._conn.execute(
                "SELECT user, assistant, embedding, dim FROM memories"
            ).fetchall()
        scored = []
        skipped = 0
        for user, assistant, emb_json, dim in rows:
            vec = json.loads(emb_json)
            # Boyut uyumsuzluğu = farklı embedding modeli → karşılaştırma anlamsız, atla.
            if (dim is not None and dim != qdim) or len(vec) != qdim:
                skipped += 1
                continue
            score = cosine(q, vec)
            if score > 0 and score >= min_score:
                scored.append((score, user, assistant))
        if skipped:
            log.debug("hafıza: %d kayıt boyut uyumsuzluğundan atlandı", skipped)
        scored.sort(key=lambda t: t[0], reverse=True)
        return [{"score": s, "user": u, "assistant": a} for s, u, a in scored[:k]]

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]


def recall_context(
    memory: MemoryStore, query: str, embedder, k: int = 3, min_score: float = 0.0
) -> str:
    """İlgili geçmiş konuşmaları modele bağlam olarak verilecek metne çevirir.

    Hafızada ilgili kayıt yoksa (ya da hepsi eşik altındaysa) boş string döner.
    """
    hits = memory.search(query, embedder, k, min_score=min_score)
    if not hits:
        return ""
    lines = ["[Geçmişten ilgili notlar — daha önce şunları konuştuk:]"]
    for h in hits:
        lines.append(f"- Sen: {h['user']}\n  Kuzgun: {h['assistant']}")
    return "\n".join(lines)
