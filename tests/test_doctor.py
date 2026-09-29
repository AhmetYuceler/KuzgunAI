"""Sağlık kontrolü /doktor (Faz C9): deterministik, enjekte edilebilir problar."""

from __future__ import annotations

from kuzgun.config import Config
from kuzgun.doctor import Check, check_claude, check_db, check_models, format_report, run_checks


def test_check_db_writable(tmp_path):
    ok, _ = check_db(str(tmp_path / "sub" / "mem.db"))
    assert ok is True  # klasör oluşturulup yazılabiliyor


def test_check_db_memory_marker():
    ok, _ = check_db(":memory:")
    assert ok is True


def test_check_claude_found_and_missing():
    assert check_claude(_which=lambda n: "C:/x/claude.cmd")[0] is True
    assert check_claude(_which=lambda n: None)[0] is False


def test_check_models_reports_missing():
    cfg = Config(model="a", coder_model="b", embed_model="c", vision_model="d")
    ok, detail = check_models(cfg, available=["a", "b"])  # c, d eksik
    assert ok is False
    assert "c" in detail and "d" in detail


def test_check_models_all_present():
    cfg = Config(model="a", coder_model="a", embed_model="a", vision_model="a")
    ok, _ = check_models(cfg, available=["a"])
    assert ok is True


def test_run_checks_returns_all_named(tmp_path):
    cfg = Config(db_path=str(tmp_path / "m.db"))
    checks = run_checks(
        cfg,
        probes={
            "ollama": lambda cfg: (True, "erişilebilir"),
            "models": lambda cfg: (True, "hepsi var"),
            "claude": lambda cfg: (True, "bulundu"),
            "db": lambda cfg: check_db(cfg.db_path),
        },
    )
    names = {c.name for c in checks}
    assert {"ollama", "models", "claude", "db"} <= names
    assert all(isinstance(c, Check) for c in checks)


def test_format_report_marks_pass_fail():
    checks = [Check("a", True, "ok"), Check("b", False, "sorun")]
    rep = format_report(checks)
    assert "a" in rep and "b" in rep
    assert "✓" in rep and "✗" in rep
