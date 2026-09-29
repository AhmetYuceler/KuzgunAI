from __future__ import annotations

import os
from dataclasses import dataclass

_VALID_MODES = ("plan", "normal", "otonom")


@dataclass(frozen=True)
class Config:
    """Kuzgun ayarları. Ortam değişkenleriyle değiştirilir; hepsinin varsayılanı var.

    Değişmezdir (frozen): bir kez `load_config()` ile yüklenir, sonra sabit kalır —
    çalışma sırasında ayar kayması olmaz (B2). Göreli yollar `load_config` içinde
    KUZGUN_HOME altına mutlaklaştırılır.
    """

    model: str = "qwen2.5:7b-instruct"
    coder_model: str = "qwen2.5-coder:7b-instruct"  # kod işleri bu modele gider
    embed_model: str = "nomic-embed-text"
    ollama_url: str = "http://localhost:11434/v1"
    api_key: str = "ollama"  # OpenAI-uyumlu arka uç anahtarı (Ollama'da sahte)
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
    memory_min_score: float = 0.70  # hafıza (RAG) alaka eşiği; altı bağlama girmez
    model_timeout: int = 300  # Ollama sohbet isteği için saniye (takılırsa vazgeç)
    claude_timeout: int = 300  # /claude ve devretme için 'claude --print' süresi
    # B2 yeni alanlar (aşağı akış: B3 arka uç, B4/B6 döngü/bağlam bütçesi):
    temperature: float = 0.2  # model üretim sıcaklığı
    max_steps: int = 10  # ajan döngüsünde azami adım
    max_history: int = 24  # bağlamda tutulan azami mesaj (sistem + son turlar)
    request_timeout: int = 300  # model HTTP isteği zaman aşımı (saniye)
    mcp_config_path: str = "mcp_servers.json"  # MCP sunucu tanımları
    # C4: genel model düşerse denenecek yedek modeller (virgülle). Boş = yedek yok.
    fallback_models: str = ""


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default  # bozuk değer başlatmayı çökertmesin


def _resolve(path: str, home: str | None) -> str:
    """Göreli yolu KUZGUN_HOME altına mutlaklaştırır. KUZGUN_HOME ayarlı DEĞİLSE
    (home None) yol olduğu gibi bırakılır (geriye dönük davranış). Boş ve
    ':memory:' her durumda korunur."""
    if not home or not path or path == ":memory:" or os.path.isabs(path):
        return path
    return os.path.normpath(os.path.join(home, path))


def load_config() -> Config:
    """Ortam değişkenlerinden (KUZGUN_*) ayarları okur, yoksa varsayılanı kullanır.

    Göreli yollar (db/notes/sessions) KUZGUN_HOME (yoksa çalışma dizini) altına
    mutlaklaştırılır; böylece Kuzgun hangi dizinden çağrılırsa çağrılsın veriyi
    aynı yerde bulur (sunucuya taşımada da tek kök)."""
    d = Config()
    home = os.environ.get("KUZGUN_HOME")  # ayarlı değilse yollar göreli kalır
    mode = os.environ.get("KUZGUN_MODE", d.mode)
    if mode not in _VALID_MODES:
        mode = d.mode
    return Config(
        mode=mode,
        model=os.environ.get("KUZGUN_MODEL", d.model),
        coder_model=os.environ.get("KUZGUN_CODER_MODEL", d.coder_model),
        embed_model=os.environ.get("KUZGUN_EMBED_MODEL", d.embed_model),
        ollama_url=os.environ.get("KUZGUN_OLLAMA_URL", d.ollama_url),
        api_key=os.environ.get("KUZGUN_API_KEY", d.api_key),
        db_path=_resolve(os.environ.get("KUZGUN_DB", d.db_path), home),
        notes_path=_resolve(os.environ.get("KUZGUN_NOTES", d.notes_path), home),
        engine_url=os.environ.get("KUZGUN_ENGINE_URL", d.engine_url),
        host=os.environ.get("KUZGUN_HOST", d.host),
        port=_int_env("KUZGUN_PORT", d.port),
        token=os.environ.get("KUZGUN_TOKEN", d.token),
        allowed_hosts=os.environ.get("KUZGUN_ALLOWED_HOSTS", d.allowed_hosts),
        autoroute=os.environ.get("KUZGUN_AUTOROUTE", "1") not in ("0", "false", "False"),
        reflect=os.environ.get("KUZGUN_REFLECT", "1") not in ("0", "false", "False"),
        vision_model=os.environ.get("KUZGUN_VISION_MODEL", d.vision_model),
        images_dir=os.environ.get("KUZGUN_IMAGES_DIR", d.images_dir),
        sessions_dir=_resolve(os.environ.get("KUZGUN_SESSIONS_DIR", d.sessions_dir), home),
        session_days=_int_env("KUZGUN_SESSION_DAYS", d.session_days),
        memory_min_score=_float_env("KUZGUN_MEMORY_MIN_SCORE", d.memory_min_score),
        model_timeout=_int_env("KUZGUN_MODEL_TIMEOUT", d.model_timeout),
        claude_timeout=_int_env("KUZGUN_CLAUDE_TIMEOUT", d.claude_timeout),
        temperature=_float_env("KUZGUN_TEMPERATURE", d.temperature),
        max_steps=_int_env("KUZGUN_MAX_STEPS", d.max_steps),
        max_history=_int_env("KUZGUN_MAX_HISTORY", d.max_history),
        request_timeout=_int_env("KUZGUN_REQUEST_TIMEOUT", d.model_timeout),
        mcp_config_path=os.environ.get("KUZGUN_MCP_CONFIG", d.mcp_config_path),
        fallback_models=os.environ.get("KUZGUN_FALLBACK_MODELS", d.fallback_models),
    )
