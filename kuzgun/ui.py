"""Terminal arayüzü: açılış başlığı (logo + sürüm + model + dizin), girdi kutusu
ve alttaki durum satırı. Claude Code'un açılış düzenine benzer.

Girdi, terminaldeyken prompt_toolkit ile (durum satırı + shift+tab mod geçişi),
boru/testte düz input() ile alınır.
"""

from __future__ import annotations

import os
import shutil
import sys

from kuzgun.permissions import MODES

# Blok karakterlerle küçük bir kuzgun (4 satır, eşit genişlik).
LOGO = (
    "  ▄▄██▄▄  ",
    " ██▀▄▀██▶ ",
    "  ▀████▀  ",
    "   ▀▀ ▀▀  ",
)
LOGO_COLOR = "medium_purple"

MODE_COLORS = {"plan": "yellow", "normal": "green", "otonom": "red"}
_HINT = 'Bir şey yaz, örn. "bu klasördeki testleri çalıştır"'


def short_path(path: str, home: str | None = None) -> str:
    """Ev dizinini ~ ile kısaltır (~\\Desktop\\LLM gibi)."""
    home = home if home is not None else os.path.expanduser("~")
    p, h = os.path.normpath(path), os.path.normpath(home)
    if os.path.normcase(p) == os.path.normcase(h):
        return "~"
    if os.path.normcase(p).startswith(os.path.normcase(h) + os.sep):
        return "~" + p[len(h) :]
    return p


def render_header(version: str, model: str, cwd: str):
    """Solda logo, sağda ad+sürüm / model / çalışma dizini."""
    from rich.table import Table
    from rich.text import Text

    logo = Text("\n".join(LOGO), style=f"bold {LOGO_COLOR}")
    info = Text()
    info.append("Kuzgun", style="bold")
    info.append(f" v{version}\n", style="dim")
    info.append(model, style="")
    info.append(" · yerel Ollama · uzman: Claude\n", style="dim")
    info.append(cwd, style="dim")
    grid = Table.grid(padding=(0, 2))
    grid.add_column(no_wrap=True)
    grid.add_column()
    grid.add_row(logo, info)
    return grid


def cycle_mode(mode: str) -> str:
    """plan → normal → otonom → plan. Tanınmayan mod 'normal'e döner."""
    if mode not in MODES:
        return "normal"
    return MODES[(MODES.index(mode) + 1) % len(MODES)]


def toggle_mode(state: dict) -> None:
    state["mode"] = cycle_mode(state.get("mode", "normal"))


def status_line(mode: str) -> str:
    return f"▶▶ {mode} mod (shift+tab ile değiştir) · /yardim"


def _width() -> int:
    return shutil.get_terminal_size((80, 24)).columns


def is_interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def make_session(state: dict, **session_kwargs):
    """Durum satırlı prompt_toolkit oturumu. shift+tab modu döndürür.

    session_kwargs (input=/output=) testte sahte girdi/çıktı vermek için."""
    from prompt_toolkit import PromptSession
    from prompt_toolkit.application import get_app
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style

    kb = KeyBindings()

    @kb.add("s-tab")
    def _(event):
        toggle_mode(state)
        event.app.invalidate()  # durum satırı hemen yenilensin

    def toolbar():
        mode = state["mode"]
        color = {"yellow": "ansiyellow", "green": "ansigreen", "red": "ansired"}[
            MODE_COLORS.get(mode, "green")
        ]
        try:
            cols = get_app().output.get_size().columns
        except Exception:  # noqa: BLE001
            cols = 0
        rule = "─" * max((cols or _width()) - 1, 20)  # -1: satır sarmasın
        return HTML(
            f"<rule>{rule}</rule>\n  <b><style fg='{color}'>▶▶ {mode} mod</style></b>"
            "<dim> (shift+tab ile değiştir) · /yardim</dim>"
        )

    style = Style.from_dict(
        {
            "bottom-toolbar": "noreverse",
            "bottom-toolbar.text": "noreverse",
            "rule": "ansibrightblack",
            "dim": "ansibrightblack",
            "prompt": "ansimagenta bold",
            "placeholder": "ansibrightblack italic",
        }
    )
    return PromptSession(
        message=[("class:prompt", "❯ ")],
        placeholder=[("class:placeholder", _HINT)],
        bottom_toolbar=toolbar,
        key_bindings=kb,
        style=style,
        **session_kwargs,
    )


def print_rule(console) -> None:
    console.print("─" * max(console.width - 1, 20), style="bright_black")


def read_input(state: dict, console, session=None) -> str:
    """Kullanıcıdan bir satır alır. EOF/Ctrl+C → EOFError/KeyboardInterrupt."""
    if session is not None:
        print_rule(console)
        return session.prompt().replace("﻿", "").strip()
    console.print(f"\n[bold cyan]\\[{state['mode']}] sen>[/] ", end="")
    return input().replace("﻿", "").strip()  # olası BOM'u temizle
