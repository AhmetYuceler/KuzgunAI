from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Kuzgun ayarları. Ortam değişkenleriyle değiştirilir; hepsinin varsayılanı var."""

    model: str = "qwen2.5:7b-instruct"
    coder_model: str = "qwen2.5-coder:7b-instruct"  # kod işleri bu modele gider
    embed_model: str = "nomic-embed-text"
    ollama_url: str = "http://localhost:11434/v1"
    db_path: str = "data/memory.db"
    notes_path: str = "data/KUZGUN.md"  # kalıcı notlar (Claude'un CLAUDE.md'si gibi)
    engine_url: str = "http://127.0.0.1:8000"
    host: str = "127.0.0.1"
    port: int = 8000
    # Güvenlik: sunucu uzağa açılırsa (host != 127.0.0.1) bir token ayarla.
    token: str = ""  # boşsa kimlik doğrulama kapalı (yalnız yerel kullanım için)
    allowed_hosts: str = "127.0.0.1,localhost"  # DNS-rebinding koruması (Host doğrulama)
    mode: str = "normal"  # başlangıç modu: plan | normal | otonom
    autoroute: bool = True  # açıkça zor işleri baştan Claude'a yönlendir
    reflect: bool = True  # kod işlerinde yazılan kodu doğrula, hatalıysa düzelttir
    vision_model: str = "qwen2.5vl:7b"  # resimli mesajlar bu modele gider
    # alt+v pano resimleri: boş → %TEMP%/kuzgun/images/<oturum>, çıkışta silinir;
    # KUZGUN_IMAGES_DIR verilirse kalıcı klasör (silinmez).
    images_dir: str = ""
    sessions_dir: str = "data/sessions"  # /resume arşivi (KUZGUN_SESSIONS_DIR)
    session_days: int = 30  # bu kadar günden eski oturumlar açılışta silinir
    model_timeout: int = 300  # Ollama sohbet isteği için saniye (takılırsa vazgeç)
    claude_timeout: int = 300  # /claude ve devretme için 'claude --print' süresi


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default  # bozuk değer başlatmayı çökertmesin


def load_config() -> Config:
    """Ortam değişkenlerinden (KUZGUN_*) ayarları okur, yoksa varsayılanı kullanır."""
    d = Config()
    mode = os.environ.get("KUZGUN_MODE", d.mode)
    if mode not in ("plan", "normal", "otonom"):
        mode = d.mode
    return Config(
        mode=mode,
        model=os.environ.get("KUZGUN_MODEL", d.model),
        coder_model=os.environ.get("KUZGUN_CODER_MODEL", d.coder_model),
        embed_model=os.environ.get("KUZGUN_EMBED_MODEL", d.embed_model),
        ollama_url=os.environ.get("KUZGUN_OLLAMA_URL", d.ollama_url),
        db_path=os.environ.get("KUZGUN_DB", d.db_path),
        notes_path=os.environ.get("KUZGUN_NOTES", d.notes_path),
        engine_url=os.environ.get("KUZGUN_ENGINE_URL", d.engine_url),
        host=os.environ.get("KUZGUN_HOST", d.host),
        port=_int_env("KUZGUN_PORT", d.port),
        token=os.environ.get("KUZGUN_TOKEN", d.token),
        allowed_hosts=os.environ.get("KUZGUN_ALLOWED_HOSTS", d.allowed_hosts),
        autoroute=os.environ.get("KUZGUN_AUTOROUTE", "1") not in ("0", "false", "False"),
        reflect=os.environ.get("KUZGUN_REFLECT", "1") not in ("0", "false", "False"),
        vision_model=os.environ.get("KUZGUN_VISION_MODEL", d.vision_model),
        images_dir=os.environ.get("KUZGUN_IMAGES_DIR", d.images_dir),
        sessions_dir=os.environ.get("KUZGUN_SESSIONS_DIR", d.sessions_dir),
        session_days=_int_env("KUZGUN_SESSION_DAYS", d.session_days),
        model_timeout=_int_env("KUZGUN_MODEL_TIMEOUT", d.model_timeout),
        claude_timeout=_int_env("KUZGUN_CLAUDE_TIMEOUT", d.claude_timeout),
    )
