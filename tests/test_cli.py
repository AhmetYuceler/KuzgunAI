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


def test_registry_has_web_tools():
    names = [s["function"]["name"] for s in build_default_registry().schemas()]
    assert "web_search" in names
    assert "fetch_url" in names


def test_web_tools_are_read_only():
    reg = build_default_registry()
    assert reg.is_mutating("web_search") is False
    assert reg.is_mutating("fetch_url") is False


def test_system_prompt_warns_about_web():
    # Not: Türkçe İ nedeniyle .lower() güvensiz; birebir substring kontrol ediyoruz.
    from kuzgun.cli import SYSTEM_PROMPT

    assert "GÜVENİLMEZ" in SYSTEM_PROMPT


def test_inject_memory_adds_relevant_context():
    from kuzgun.cli import inject_memory
    from kuzgun.memory import Memory
    from kuzgun.embeddings import FakeEmbedder

    m = Memory(":memory:")
    e = FakeEmbedder()
    m.add("python nedir", "python bir dildir", e)
    messages = []
    inject_memory(messages, m, e, "python hakkinda bilgi")
    assert len(messages) == 1 and messages[0]["role"] == "system"
    assert "python nedir" in messages[0]["content"]


def test_inject_memory_empty_adds_nothing():
    from kuzgun.cli import inject_memory
    from kuzgun.memory import Memory
    from kuzgun.embeddings import FakeEmbedder

    messages = []
    inject_memory(messages, Memory(":memory:"), FakeEmbedder(), "soru")
    assert messages == []


def test_format_history_shows_recent_turns():
    from kuzgun.cli import format_history

    msgs = [
        {"role": "system", "content": "sistem promptu"},
        {"role": "user", "content": "soru bir"},
        {"role": "assistant", "content": "cevap bir"},
    ]
    out = format_history(msgs)
    assert "soru bir" in out
    assert "cevap bir" in out
    assert "sistem promptu" not in out  # sistem mesajı gösterilmez


def test_format_history_empty():
    from kuzgun.cli import format_history

    assert "boş" in format_history([{"role": "system", "content": "x"}]).lower()


def test_registry_has_ask_expert_read_only():
    reg = build_default_registry()
    names = [s["function"]["name"] for s in reg.schemas()]
    assert "ask_expert" in names
    assert reg.is_mutating("ask_expert") is False


def test_yardim_mentions_claude():
    out = handle_slash("/yardim", {"mode": "normal"})
    assert "claude" in out.lower()


def test_slash_commands_without_argument_show_usage():
    for cmd in ("/hatirla", "/ajanlar", "/claude"):
        out = handle_slash(cmd, {"mode": "normal"})
        assert "Kullanım" in out and cmd in out


def test_mode_shortcut_commands_switch_mode():
    state = {"mode": "normal"}
    assert "plan" in handle_slash("/plan", state)
    assert state["mode"] == "plan"
    handle_slash("/otonom", state)
    assert state["mode"] == "otonom"
    handle_slash("/normal", state)
    assert state["mode"] == "normal"


def test_mode_shortcut_with_task_queues_it():
    # '/plan https://x.com/... bu sayfaya eriş' → plan moduna geç VE görevi işle
    state = {"mode": "normal"}
    handle_slash("/plan şu sayfaya bak ve özetle", state)
    assert state["mode"] == "plan"
    assert state["pending"] == "şu sayfaya bak ve özetle"


def test_unknown_command_suggests_closest():
    out = handle_slash("/gecmiş", {"mode": "normal"})
    assert "/gecmis" in out


def test_unknown_command_without_match_points_to_help():
    out = handle_slash("/resume", {"mode": "normal"})
    assert "/yardim" in out


def test_run_guarded_returns_cancel_message_on_ctrl_c():
    from kuzgun.cli import run_guarded

    def boom():
        raise KeyboardInterrupt

    assert "iptal" in run_guarded(boom).lower()
    assert run_guarded(lambda: "ok") == "ok"
    assert run_guarded(lambda: 1 / 0).startswith("[hata]")
