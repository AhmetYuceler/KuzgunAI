from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from kuzgun.embeddings import cosine


class Memory:
    """Konuşmaları SQLite'ta embedding ile saklayan, benzerlikle arayan hafıza.

    Sınırsız büyür; taşınabilir tek dosyadır (db_path). ':memory:' geçici bellek.
    """

    def __init__(self, db_path: str = "data/memory.db"):
        self._db_path = str(db_path)
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS memories ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, "
            "user TEXT, assistant TEXT, embedding TEXT)"
        )
        self._conn.commit()

    def add(self, user_text: str, assistant_text: str, embedder) -> None:
        emb = embedder.embed(f"{user_text}\n{assistant_text}")
        self._conn.execute(
            "INSERT INTO memories (ts, user, assistant, embedding) VALUES (?, ?, ?, ?)",
            (time.time(), user_text, assistant_text, json.dumps(emb)),
        )
        self._conn.commit()

    def search(self, query: str, embedder, k: int = 3) -> list[dict]:
        q = embedder.embed(query)
        rows = self._conn.execute(
            "SELECT user, assistant, embedding FROM memories"
        ).fetchall()
        scored = []
        for user, assistant, emb_json in rows:
            score = cosine(q, json.loads(emb_json))
            if score > 0:
                scored.append((score, user, assistant))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [
            {"score": s, "user": u, "assistant": a} for s, u, a in scored[:k]
        ]

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
