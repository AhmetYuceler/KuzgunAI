import os
from rich.console import Console

from kuzgun.ui import (
    LOGO,
    MODE_COLORS,
    cycle_mode,
    render_header,
    short_path,
    status_line,
    toggle_mode,
)


def _render(renderable) -> str:
    console = Console(record=True, width=100, force_terminal=False, color_system=None)
    console.print(renderable)
    return console.export_text()


def test_logo_is_small_rectangular_block():
    assert 3 <= len(LOGO) <= 6
    assert len({len(line) for line in LOGO}) == 1  # tüm satırlar eşit genişlikte


def test_short_path_replaces_home_with_tilde():
    assert short_path(r"C:\Users\ahmet\Desktop\LLM", home=r"C:\Users\ahmet") == r"~\Desktop\LLM"


def test_short_path_keeps_other_paths():
    assert short_path(r"D:\proje", home=r"C:\Users\ahmet") == r"D:\proje"


def test_short_path_home_itself():
    assert short_path(r"C:\Users\ahmet", home=r"C:\Users\ahmet") == "~"


def test_header_shows_name_version_model_and_cwd():
    out = _render(render_header(version="0.1.0", model="qwen2.5:7b-instruct", cwd=r"~\Desktop\LLM"))
    assert "Kuzgun" in out
    assert "v0.1.0" in out
    assert "qwen2.5:7b-instruct" in out
    assert r"~\Desktop\LLM" in out
    assert LOGO[0].strip() in out  # logo da basılıyor


def test_cycle_mode_goes_around():
    assert cycle_mode("plan") == "normal"
    assert cycle_mode("normal") == "otonom"
    assert cycle_mode("otonom") == "plan"
    assert cycle_mode("bilinmeyen") == "normal"  # tanınmayan mod güvenli varsayılana döner


def test_toggle_mode_mutates_state():
    state = {"mode": "normal"}
    toggle_mode(state)
    assert state["mode"] == "otonom"


def test_status_line_mentions_mode_and_shortcut():
    out = status_line("plan")
    assert "plan" in out
    assert "shift+tab" in out


def test_every_mode_has_a_color():
    for m in ("plan", "normal", "otonom"):
        assert m in MODE_COLORS


def test_session_shift_tab_cycles_mode_and_returns_line():
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    from kuzgun.ui import make_session

    state = {"mode": "normal"}
    with create_pipe_input() as inp:
        session = make_session(state, input=inp, output=DummyOutput())
        inp.send_text("\x1b[Z")  # shift+tab
        inp.send_text("merhaba\r")
        assert session.prompt() == "merhaba"
    assert state["mode"] == "otonom"
    assert "otonom" in str(session.bottom_toolbar())  # durum satırı yeni modu gösterir


def test_alt_v_attaches_clipboard_image(tmp_path):
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    from kuzgun.ui import make_session

    state = {"mode": "normal", "grab": lambda: str(tmp_path / "pano.png")}
    with create_pipe_input() as inp:
        session = make_session(state, input=inp, output=DummyOutput())
        inp.send_text("\x1bv")  # alt+v
        inp.send_text("bu ne\r")
        line = session.prompt()
    assert state["attachments"] == [str(tmp_path / "pano.png")]
    assert "[resim 1]" in line and "bu ne" in line


def test_interactive_loop_queues_messages_while_busy():
    import asyncio
    import time

    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput
    from rich.console import Console

    from kuzgun.ui import run_interactive

    handled = []

    def handle(text, images, cancel):
        time.sleep(0.15)  # meşgulken ikinci mesaj gelir → sıraya girmeli
        handled.append(text)

    state = {"mode": "normal"}
    console = Console(file=open(os.devnull, "w", encoding="utf-8"), force_terminal=False)
    from prompt_toolkit.application import create_app_session

    with create_pipe_input() as inp, create_app_session(input=inp, output=DummyOutput()):
        inp.send_text("birinci\r")
        inp.send_text("ikinci\r")
        inp.close()  # EOF → döngü biter, süren iş beklenir
        asyncio.run(run_interactive(state, console, handle))
    assert handled == ["birinci", "ikinci"]


def test_interactive_loop_ends_when_handle_sets_quit():
    import asyncio

    from prompt_toolkit.application import create_app_session
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput
    from rich.console import Console

    from kuzgun.ui import run_interactive

    handled = []

    def handle(text, images, cancel):
        handled.append(text)
        state["quit"] = True  # /cikis gibi

    state = {"mode": "normal"}
    console = Console(file=open(os.devnull, "w", encoding="utf-8"), force_terminal=False)
    with create_pipe_input() as inp, create_app_session(input=inp, output=DummyOutput()):
        inp.send_text("/cikis\r")
        # EOF gönderilmiyor: döngü quit ile kendiliğinden bitmeli (asılı kalmamalı)
        asyncio.run(asyncio.wait_for(run_interactive(state, console, handle), timeout=5))
    assert handled == ["/cikis"]


def test_set_title_writes_osc_sequence():
    import io

    from kuzgun.ui import set_title

    out = io.StringIO()
    set_title("Kuzgun — renk testi", file=out)
    assert out.getvalue() == "\x1b]0;Kuzgun — renk testi\x07"


def test_set_title_strips_control_chars():
    import io

    from kuzgun.ui import set_title

    out = io.StringIO()
    set_title("a\x07b\x1bc\nd", file=out)
    assert out.getvalue() == "\x1b]0;abcd\x07"


def _completions(completer, text):
    from prompt_toolkit.completion import CompleteEvent
    from prompt_toolkit.document import Document

    return list(completer.get_completions(Document(text, len(text)), CompleteEvent()))


def test_slash_completer_lists_commands_with_descriptions():
    from kuzgun.ui import SlashCompleter

    c = SlashCompleter(
        {"/resume": "eski oturuma dön", "/rename": "oturuma ad ver", "/cikis": "çık"},
        needs_arg={"/resume", "/rename"},
    )
    got = _completions(c, "/re")
    assert [x.text for x in got] == ["/resume ", "/rename "]  # sıra korunur, öneki eşleşir
    assert "eski oturuma dön" in str(got[0].display_meta_text)
    assert got[0].start_position == -3  # '/re' yerine yazılır
    assert [x.text for x in _completions(c, "/")][-1] == "/cikis"  # argümansız komut: boşluk yok


def test_slash_completer_no_completion_for_plain_text():
    from kuzgun.ui import SlashCompleter

    assert _completions(SlashCompleter({"/cikis": "çık"}), "merhaba") == []


def test_slash_completer_completes_arguments_from_choices():
    from kuzgun.ui import SlashCompleter

    c = SlashCompleter(
        {"/mod": "mod değiştir", "/resume": "oturuma dön"},
        arg_choices={
            "/mod": lambda: ["plan", "normal", "otonom"],
            "/resume": lambda: [("renk-testi", "benim en sevdigim renk"), ("2", "başka")],
        },
    )
    assert [x.text for x in _completions(c, "/mod n")] == ["normal"]
    got = _completions(c, "/resume ")
    assert [x.text for x in got] == ["renk-testi", "2"]
    assert "benim en sevdigim" in str(got[0].display_meta_text)


def test_session_has_completer_when_commands_given():
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    from kuzgun.ui import make_session

    with create_pipe_input() as inp:
        s = make_session({"mode": "normal"}, commands={"/cikis": "çık"}, input=inp, output=DummyOutput())
        assert s.completer is not None
        assert bool(s.complete_while_typing) is True


def _prompt_with_keys(keys: str) -> str:
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    from kuzgun.ui import make_session

    with create_pipe_input() as inp:
        session = make_session({"mode": "normal"}, input=inp, output=DummyOutput())
        inp.send_text(keys)
        return session.prompt()


def test_ctrl_w_deletes_previous_word():
    assert _prompt_with_keys("merhaba dunya\x17\r") == "merhaba "


def test_ctrl_delete_deletes_next_word_and_ctrl_arrows_jump_words():
    # Home, Ctrl+Delete → 'abc' silinir; sonra Ctrl+→ ile 'def' sonuna gidip 'X' yaz
    assert _prompt_with_keys("abc def\x1b[H\x1b[3;5~\x1b[1;5CX\r") == " defX"


def test_ctrl_u_and_ctrl_k_kill_line_parts():
    assert _prompt_with_keys("silinecek kalan\x1b[1;5D\x15\r") == "kalan"  # Ctrl+← sonra Ctrl+U
    assert _prompt_with_keys("kalan silinecek\x1b[1;5D\x0b\r") == "kalan "  # Ctrl+← sonra Ctrl+K


def test_ctrl_backspace_becomes_word_delete_on_windows():
    import sys

    import pytest

    from kuzgun.ui import _enable_ctrl_backspace

    if sys.platform != "win32":
        pytest.skip("Win32 konsol girdisi")
    from prompt_toolkit.input.win32 import ConsoleInputReader
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.win32_types import KEY_EVENT_RECORD

    _enable_ctrl_backspace()
    _enable_ctrl_backspace()  # iki kez çağrılınca üst üste sarmalamaz

    def ev(char, vk, ctrl):
        e = KEY_EVENT_RECORD()
        e.KeyDown = 1
        e.VirtualKeyCode = vk
        e.ControlKeyState = ConsoleInputReader.LEFT_CTRL_PRESSED if ctrl else 0
        e.uChar.UnicodeChar = char
        return e

    reader = ConsoleInputReader.__new__(ConsoleInputReader)
    assert [k.key for k in reader._event_to_key_presses(ev("", 0x08, ctrl=True))] == [Keys.ControlW]
    assert [k.key for k in reader._event_to_key_presses(ev("", 0x08, ctrl=False))] == [Keys.ControlH]
    assert [k.key for k in reader._event_to_key_presses(ev("a", 0x41, ctrl=False))] == ["a"]
