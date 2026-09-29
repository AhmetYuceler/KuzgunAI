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
