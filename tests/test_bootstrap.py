"""bootstrap: somut kurulum tek yerde; araçlar config'e bağımlı değil (Faz B3)."""

from __future__ import annotations


def test_openai_compat_backend_alias():
    from kuzgun.models import OllamaClient, OpenAICompatBackend

    assert OllamaClient is OpenAICompatBackend  # eski ad takma ad olarak korunur


def test_build_default_registry_has_core_tools(tmp_config):
    from kuzgun.bootstrap import build_default_registry

    reg = build_default_registry(tmp_config)
    for name in ("read_file", "write_file", "run_command", "remember", "web_search"):
        assert reg.has(name), name
    assert reg.is_mutating("remember") is True


def test_remember_bound_to_config_notes_path(tmp_config):
    # B3 (ToolContext): registry, remember'ı config'in notes_path'ine bağlar; model
    # yalnız 'fact' geçer, yol partial ile gelir → remember artık load_config çağırmaz.
    from kuzgun.bootstrap import build_default_registry
    from kuzgun.notebook import load_notes

    reg = build_default_registry(tmp_config)
    out = reg.execute("remember", {"fact": "kullanıcı çayı sever"})
    assert not out.startswith("Error:")
    assert "çayı sever" in load_notes(tmp_config.notes_path)


def test_remember_module_does_not_import_config():
    import ast
    import pathlib

    src = pathlib.Path("kuzgun/tools/remember.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imports = [
        n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module
    ]
    assert not any("config" in (m or "") for m in imports), "remember config'e bağımlı olmamalı"


def test_build_engine_returns_configured_engine(tmp_config):
    from kuzgun.bootstrap import build_engine
    from kuzgun.engine import KuzgunEngine

    eng = build_engine(config=tmp_config)
    assert isinstance(eng, KuzgunEngine)
    assert eng.config is tmp_config
    assert eng.registry.has("read_file")


def test_build_engine_accepts_dependency_overrides(tmp_config):
    from kuzgun.bootstrap import build_engine
    from kuzgun.embeddings import FakeEmbedder
    from kuzgun.memory import Memory
    from kuzgun.models import AssistantMessage, FakeModelClient
    from kuzgun.tools import ToolRegistry

    eng = build_engine(
        config=tmp_config,
        client=FakeModelClient([AssistantMessage(text="merhaba", tool_calls=[])]),
        embedder=FakeEmbedder(),
        memory=Memory(":memory:"),
        registry=ToolRegistry(),
    )
    assert eng.chat("selam") == "merhaba"
