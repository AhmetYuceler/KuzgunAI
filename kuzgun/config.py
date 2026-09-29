from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Kuzgun ayarları. Ortam değişkenleriyle değiştirilir; hepsinin varsayılanı var."""

    model: str = "qwen2.5:7b-instruct"
    embed_model: str = "nomic-embed-text"
    ollama_url: str = "http://localhost:11434/v1"
    db_path: str = "data/memory.db"
    engine_url: str = "http://127.0.0.1:8000"
    host: str = "127.0.0.1"
    port: int = 8000
    # Güvenlik: sunucu uzağa açılırsa (host != 127.0.0.1) bir token ayarla.
    token: str = ""  # boşsa kimlik doğrulama kapalı (yalnız yerel kullanım için)
    allowed_hosts: str = "127.0.0.1,localhost"  # DNS-rebinding koruması (Host doğrulama)


def load_config() -> Config:
    """Ortam değişkenlerinden (KUZGUN_*) ayarları okur, yoksa varsayılanı kullanır."""
    d = Config()
    return Config(
        model=os.environ.get("KUZGUN_MODEL", d.model),
        embed_model=os.environ.get("KUZGUN_EMBED_MODEL", d.embed_model),
        ollama_url=os.environ.get("KUZGUN_OLLAMA_URL", d.ollama_url),
        db_path=os.environ.get("KUZGUN_DB", d.db_path),
        engine_url=os.environ.get("KUZGUN_ENGINE_URL", d.engine_url),
        host=os.environ.get("KUZGUN_HOST", d.host),
        port=int(os.environ.get("KUZGUN_PORT", str(d.port))),
        token=os.environ.get("KUZGUN_TOKEN", d.token),
        allowed_hosts=os.environ.get("KUZGUN_ALLOWED_HOSTS", d.allowed_hosts),
    )
