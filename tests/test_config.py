from kuzgun.config import Config, load_config

_ENV_KEYS = [
    "KUZGUN_MODEL",
    "KUZGUN_EMBED_MODEL",
    "KUZGUN_OLLAMA_URL",
    "KUZGUN_DB",
    "KUZGUN_ENGINE_URL",
    "KUZGUN_HOST",
    "KUZGUN_PORT",
]


def test_defaults(monkeypatch):
    for k in _ENV_KEYS:
        monkeypatch.delenv(k, raising=False)
    c = load_config()
    assert isinstance(c, Config)
    assert c.model == "qwen2.5:7b-instruct"
    assert c.embed_model == "nomic-embed-text"
    assert c.db_path == "data/memory.db"
    assert c.port == 8000


def test_mode_default_and_env(monkeypatch):
    monkeypatch.delenv("KUZGUN_MODE", raising=False)
    assert load_config().mode == "normal"
    monkeypatch.setenv("KUZGUN_MODE", "otonom")
    assert load_config().mode == "otonom"


def test_mode_invalid_falls_back_to_normal(monkeypatch):
    monkeypatch.setenv("KUZGUN_MODE", "gecersiz")
    assert load_config().mode == "normal"


def test_reads_env(monkeypatch):
    monkeypatch.setenv("KUZGUN_MODEL", "llama3.1:8b")
    monkeypatch.setenv("KUZGUN_PORT", "9000")
    monkeypatch.setenv("KUZGUN_DB", "/veri/x.db")
    c = load_config()
    assert c.model == "llama3.1:8b"
    assert c.port == 9000  # int'e çevrilmeli
    assert c.db_path == "/veri/x.db"


def test_invalid_port_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("KUZGUN_PORT", "abc")
    assert load_config().port == 8000


def test_claude_timeout_env(monkeypatch):
    monkeypatch.delenv("KUZGUN_CLAUDE_TIMEOUT", raising=False)
    assert load_config().claude_timeout == 300
    monkeypatch.setenv("KUZGUN_CLAUDE_TIMEOUT", "600")
    assert load_config().claude_timeout == 600


def test_vision_model_and_images_dir_defaults(monkeypatch):
    c = load_config()
    assert c.vision_model == "qwen2.5vl:7b"
    assert c.images_dir == ""  # boş → oturumluk geçici klasör
    monkeypatch.setenv("KUZGUN_VISION_MODEL", "llava:7b")
    assert load_config().vision_model == "llava:7b"


def test_images_dir_default_empty_means_session_temp(monkeypatch):
    assert load_config().images_dir == ""  # boş → oturumluk geçici klasör, çıkışta silinir
    monkeypatch.setenv("KUZGUN_IMAGES_DIR", "C:/kalici")
    assert load_config().images_dir == "C:/kalici"


def test_sessions_dir_and_days(monkeypatch):
    c = load_config()
    assert c.sessions_dir == "data/sessions" and c.session_days == 30
    monkeypatch.setenv("KUZGUN_SESSION_DAYS", "7")
    assert load_config().session_days == 7
