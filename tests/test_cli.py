from kuzgun.cli import build_default_registry, handle_slash


def test_default_registry_has_all_faz2_tools():
    reg = build_default_registry()
    names = [s["function"]["name"] for s in reg.schemas()]
    for t in ("read_file", "write_file", "run_command", "glob_search", "grep_search"):
        assert t in names


def test_mutating_tools_flagged():
    reg = build_default_registry()
    assert reg.is_mutating("write_file") is True
    assert reg.is_mutating("run_command") is True
    assert reg.is_mutating("read_file") is False


def test_slash_mod_changes_state():
    state = {"mode": "normal"}
    handle_slash("/mod plan", state)
    assert state["mode"] == "plan"


def test_slash_invalid_mode_keeps_state():
    state = {"mode": "normal"}
    out = handle_slash("/mod ucmaz", state)
    assert state["mode"] == "normal"
    assert out is not None  # kullanıcıya uyarı döndürür


def test_non_slash_returns_none():
    assert handle_slash("merhaba", {"mode": "normal"}) is None
