"""Kalıcı log: Kuzgun ne yaptığını dosyaya yazar (geliştirme döngüsü — kullanıcı
çalıştırır, biz logu okuyup hataları teşhis ederiz). TUI'yi bozmamak için ekrana
(stderr) değil sadece dosyaya yazabilmeli.
"""

from __future__ import annotations

import logging


def test_config_has_log_defaults():
    from kuzgun.config import Config

    c = Config()
    assert c.log_file.endswith("kuzgun.log")
    assert c.log_level == "INFO"


def test_log_file_env_override(monkeypatch):
    from kuzgun.config import load_config

    monkeypatch.setenv("KUZGUN_LOG_LEVEL", "DEBUG")
    cfg = load_config()
    assert cfg.log_level == "DEBUG"


def test_setup_logging_file_only(tmp_path):
    import kuzgun.logging_setup as L

    root = logging.getLogger("kuzgun")
    prev_handlers, prev_conf = list(root.handlers), L._configured
    root.handlers.clear()
    L._configured = False
    try:
        logf = tmp_path / "k.log"
        L.setup_logging("INFO", str(logf), console=False)
        L.get_logger("t").info("merhaba-log")
        for h in root.handlers:
            h.flush()
        assert "merhaba-log" in logf.read_text(encoding="utf-8")
        # console=False → stderr (düz StreamHandler) handler'ı OLMAMALI
        plain_stream = [
            h
            for h in root.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        ]
        assert plain_stream == []
    finally:
        for h in root.handlers:
            h.close()
        root.handlers[:] = prev_handlers
        L._configured = prev_conf
