"""Config donması, yeni alanlar, KUZGUN_HOME yol çözümü, doğrulama (Faz B2)."""

from __future__ import annotations

import dataclasses
import os

import pytest

from kuzgun.config import Config, load_config


def test_config_is_frozen():
    cfg = Config()
    with pytest.raises(dataclasses.FrozenInstanceError):
        cfg.model = "baska"  # değiştirilemez (bir kez yükle, dondur)


def test_new_fields_have_defaults():
    cfg = Config()
    assert cfg.api_key == "ollama"
    assert isinstance(cfg.temperature, float)
    assert cfg.max_steps >= 1
    assert cfg.max_history >= 2
    assert cfg.request_timeout >= 1
    assert cfg.mcp_config_path
    assert cfg.memory_min_score >= 0.0


def test_load_config_reads_new_env(monkeypatch):
    monkeypatch.setenv("KUZGUN_TEMPERATURE", "0.7")
    monkeypatch.setenv("KUZGUN_MAX_STEPS", "5")
    monkeypatch.setenv("KUZGUN_MAX_HISTORY", "40")
    monkeypatch.setenv("KUZGUN_MEMORY_MIN_SCORE", "0.3")
    cfg = load_config()
    assert cfg.temperature == 0.7
    assert cfg.max_steps == 5
    assert cfg.max_history == 40
    assert cfg.memory_min_score == 0.3


def test_relative_paths_resolved_under_home(monkeypatch, tmp_path):
    monkeypatch.setenv("KUZGUN_HOME", str(tmp_path))
    monkeypatch.delenv("KUZGUN_DB", raising=False)
    cfg = load_config()
    assert os.path.isabs(cfg.db_path)
    assert str(tmp_path) in cfg.db_path        # göreli varsayılan HOME altına çözüldü
    assert os.path.isabs(cfg.notes_path)


def test_absolute_path_env_is_kept(monkeypatch, tmp_path):
    abs_db = str(tmp_path / "x" / "m.db")
    monkeypatch.setenv("KUZGUN_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("KUZGUN_DB", abs_db)
    cfg = load_config()
    assert cfg.db_path == abs_db               # mutlak yol HOME'a taşınmaz


def test_memory_scope_stays_in_memory_marker(monkeypatch):
    # ':memory:' özel değeri yol çözümünden etkilenmemeli.
    monkeypatch.setenv("KUZGUN_HOME", "/tmp/whatever")
    monkeypatch.setenv("KUZGUN_DB", ":memory:")
    assert load_config().db_path == ":memory:"


def test_invalid_port_falls_back(monkeypatch):
    monkeypatch.setenv("KUZGUN_PORT", "bozuk")
    assert load_config().port == Config().port
