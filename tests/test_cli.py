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


def test_resume_command_lists_and_picks(tmp_path):
    from kuzgun.archive import SessionArchive
    from kuzgun.cli import resume_session

    a = SessionArchive(str(tmp_path))
    sid = a.new_id()
    a.save(sid, [{"role": "system", "content": "s"}, {"role": "user", "content": "eski soru"},
                 {"role": "assistant", "content": "eski cevap"}])

    class Eng:
        messages = [{"role": "system", "content": "yeni sistem"}]

    eng = Eng()
    state = {"session_id": "x"}
    # argümansız: yalnız liste (seçim ayrı komutla), oturum değişmez
    out = resume_session(eng, a, "", state)
    assert "eski soru" in out and "/resume <no>" in out
    assert state["session_id"] == "x"
    out = resume_session(eng, a, "1", state)  # numarayla seç
    assert "eski soru" in out
    assert state["session_id"] == sid
    assert eng.messages[0]["content"] == "yeni sistem"  # sistem promptu güncel kalır
    assert eng.messages[1]["content"] == "eski soru"


def test_resume_command_by_name_and_missing(tmp_path):
    from kuzgun.archive import SessionArchive
    from kuzgun.cli import resume_session

    a = SessionArchive(str(tmp_path))
    sid = a.new_id()
    a.save(sid, [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}])
    a.rename(sid, "isim")

    class Eng:
        messages = [{"role": "system", "content": "s"}]

    state = {}
    assert "isim" in resume_session(Eng(), a, "isim", state)
    assert state["session_id"] == sid
    assert "bulunamadı" in resume_session(Eng(), a, "yok", {})
    assert "yok" in resume_session(Eng(), SessionArchive(str(tmp_path / "bos")), "", {}).lower()


def test_yardim_mentions_resume():
    out = handle_slash("/yardim", {"mode": "normal"})
    assert "/resume" in out and "/rename" in out


def test_parse_args_continue_resume_name():
    from kuzgun.cli import _parse_args

    assert _parse_args(["-c"]).cont is True
    assert _parse_args(["--resume"]).resume == ""  # boş → listeden seç
    assert _parse_args(["--resume", "isim"]).resume == "isim"
    assert _parse_args([]).resume is None
    assert _parse_args(["-n", "auth"]).name == "auth"


def test_format_session_list_numbers_and_titles():
    from kuzgun.cli import format_session_list

    out = format_session_list([{"id": "a", "name": "isim", "title": "baslik", "updated": 0, "turns": 3}])
    assert out.startswith(" 1. isim") and "baslik" in out and "3 tur" in out
    assert "yok" in format_session_list([]).lower()


def test_session_title_prefers_name_then_first_message():
    from kuzgun.cli import session_title

    assert session_title({"name": "renk-testi", "title": "benim en sevdigim"}) == "renk-testi"
    assert session_title({"name": "", "title": "benim en sevdigim renk mor"}) == "benim en sevdigim renk mor"
    assert session_title({"name": "", "title": "x" * 80}) == "x" * 47 + "..."
    assert session_title({}) == "Kuzgun"


def test_command_help_covers_all_commands():
    from kuzgun.cli import COMMAND_HELP, COMMANDS

    assert set(COMMAND_HELP) == set(COMMANDS)
    assert all(COMMAND_HELP[c] for c in COMMANDS)


def test_resume_lists_current_folder_first_and_all_on_request(tmp_path):
    from kuzgun.archive import SessionArchive
    from kuzgun.cli import resume_session

    a = SessionArchive(str(tmp_path))
    here, other = a.new_id(), a.new_id()
    a.save(here, [{"role": "user", "content": "bu klasör"}, {"role": "assistant", "content": "a"}], cwd="C:/p1")
    a.save(other, [{"role": "user", "content": "başka klasör"}, {"role": "assistant", "content": "b"}], cwd="C:/p2")

    class Eng:
        messages = [{"role": "system", "content": "s"}]

    state = {"cwd": "C:/p1"}
    out = resume_session(Eng(), a, "", state)
    assert "bu klasör" in out and "başka klasör" not in out  # bu klasörün oturumları
    assert "hepsi" in out  # ipucu: /resume hepsi
    out = resume_session(Eng(), a, "hepsi", state)
    assert "bu klasör" in out and "başka klasör" in out
    resume_session(Eng(), a, "1", state)  # numara, bu klasörün listesine göre
    assert state["session_id"] == here
