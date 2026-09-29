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
