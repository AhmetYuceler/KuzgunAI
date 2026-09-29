"""Ortak test altyapısı (Faz A0).

- `clean_env`: her testte KUZGUN_* ortam değişkenlerini temizler (testler arası
  sızıntı olmasın — biri KUZGUN_MODE ayarlarsa diğerini etkilemesin).
- `tmp_config`: geçici yollarla (db/notes) açık bir Config üretir.
- `engine`: FakeModelClient + FakeEmbedder + bellek-içi hafıza + boş registry ile
  hazır bir KuzgunEngine döndüren fabrika. Testler kendi scripted mesajlarını verir.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """KUZGUN_* değişkenlerini her testten önce kaldır (izolasyon)."""
    import os

    for key in [k for k in os.environ if k.startswith("KUZGUN_")]:
        monkeypatch.delenv(key, raising=False)
    yield


@pytest.fixture
def tmp_config(tmp_path):
    from kuzgun.config import Config

    return Config(
        db_path=str(tmp_path / "memory.db"),
        notes_path=str(tmp_path / "KUZGUN.md"),
    )


@pytest.fixture
def make_engine(tmp_config):
    """Scripted mesaj listesi (+ istege bagli registry) alan bir engine fabrikasi."""
    from kuzgun.embeddings import FakeEmbedder
    from kuzgun.engine import KuzgunEngine
    from kuzgun.memory import Memory
    from kuzgun.models import FakeModelClient
    from kuzgun.tools import ToolRegistry

    def _make(scripted=None, registry=None, **kwargs):
        return KuzgunEngine(
            client=FakeModelClient(scripted or []),
            embedder=FakeEmbedder(),
            memory=Memory(":memory:"),
            registry=registry if registry is not None else ToolRegistry(),
            config=tmp_config,
            **kwargs,
        )

    return _make
