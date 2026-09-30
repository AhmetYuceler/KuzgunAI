"""Terminal arayüzü: açılış başlığı (logo + sürüm + model + dizin), altta sabit
girdi kutusu + durum satırı, üstte akan konuşma. Claude Code'un düzenine benzer.

İşleyiş (etkileşimli terminalde):
- Girdi kutusu HER ZAMAN ekranın altında kalır; Kuzgun çalışırken de.
- Çalışırken yazılan mesajlar sıraya girer ve sırayla işlenir.
- Durum satırı: mod (shift+tab döndürür), çalışırken dönen simge, sıradaki mesaj sayısı.
- alt+v: panodaki resmi mesaja ekler (görsel model analiz eder).
- Ctrl+C: çalışan işi iptal eder; boş kutuda ikinci Ctrl+C çıkar.

Terminal değilse (boru/test) düz input() ile eş zamanlı çalışır.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import threading
import time

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
_ANSI = {"yellow": "ansiyellow", "green": "ansigreen", "red": "ansired"}
_HINT = 'Bir şey yaz · alt+v pano resmi ekler · örn. "bu klasördeki testleri çalıştır"'
_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

_LOOP: asyncio.AbstractEventLoop | None = None  # etkileşimli döngü (confirm için)


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


# ---- konuşma çıktısı (Claude Code görünümü: '❯ sen', '● cevap') ----------------


def print_user(console, text: str, images: list[str] | None = None) -> None:
    from rich.text import Text

    t = Text("❯ ", style="bold magenta")
    t.append(text, style="bold")
    if images:
        t.append(f"  [{len(images)} resim]", style="dim")
    console.print(t)


def print_reply(console, markdown: str, who: str = "kuzgun") -> None:
    """'● ' işaretiyle, 2 boşluk içeriden markdown cevap."""
    from rich.markdown import Markdown
    from rich.table import Table

    color = {"kuzgun": "green", "claude": "magenta", "ajanlar": "cyan"}.get(who, "green")
    grid = Table.grid(padding=(0, 1))
    grid.add_column(no_wrap=True)
    grid.add_column()
    label = "●" if who == "kuzgun" else f"● [{color}]{who}:[/]"
    grid.add_row(f"[bold {color}]{label}[/]", Markdown(markdown))
    console.print(grid)
    console.print()


def print_note(console, text: str, style: str = "yellow") -> None:
    console.print(f"  [{style}]{text}[/]")
    console.print()


# ---- slash komut tamamlama (Claude Code'daki '/' menüsü gibi) --------------------


class SlashCompleter:
    """'/' ile başlayan girdide komutları (yanında soluk açıklama) önerir; ↑/↓ ile
    gezilir, Tab tamamlar. Komuttan sonra boşluk gelince, varsa o komutun
    argüman seçeneklerini (arg_choices[cmd]() → ['x'] ya da [('x', 'açıklama')]) önerir.

    Argüman alan komutlar (`needs_arg`) tamamlanınca sonuna boşluk eklenir.
    """

    def __init__(self, commands: dict[str, str], arg_choices=None, needs_arg=None):
        from prompt_toolkit.completion import Completer

        self._commands = commands
        self._arg_choices = arg_choices or {}
        self._needs_arg = set(needs_arg) if needs_arg is not None else set(self._arg_choices)
        # Completer arayüzü (prompt_toolkit soyut sınıfı) — isinstance için kaydet.
        Completer.register(type(self))

    def get_completions(self, document, complete_event):
        from prompt_toolkit.completion import Completion

        text = document.text_before_cursor
        if not text.startswith("/"):
            return
        if " " not in text:  # komut adı yazılıyor
            for cmd, desc in self._commands.items():
                if cmd.startswith(text):
                    suffix = " " if cmd in self._needs_arg or cmd in self._arg_choices else ""
                    yield Completion(cmd + suffix, start_position=-len(text), display=cmd, display_meta=desc)
            return
        cmd, _, arg = text.partition(" ")
        choices = self._arg_choices.get(cmd)
        if choices is None:
            return
        for item in choices():
            value, meta = (item, "") if isinstance(item, str) else item
            if value.startswith(arg):
                yield Completion(value, start_position=-len(arg), display_meta=meta)

    async def get_completions_async(self, document, complete_event):
        for c in self.get_completions(document, complete_event):
            yield c


# ---- prompt_toolkit oturumu ----------------------------------------------------

# Düzenleme kısayolları (Claude Code'daki gibi; prompt_toolkit emacs varsayılanları):
#   Ctrl+Backspace / Ctrl+W  önceki kelimeyi sil     Ctrl+Delete  sonraki kelimeyi sil
#   Ctrl+←/→                 kelime kelime git       Home/End, Ctrl+A/E  satır başı/sonu
#   Ctrl+U                   imleçten başa kadar sil Ctrl+K       imleçten sona kadar sil
#   ↑/↓                      önceki girdiler         Ctrl+C       iptal/temizle/çık
EDIT_KEYS_HELP = (
    "Kısayollar: Ctrl+Backspace/Ctrl+Delete kelime sil · Ctrl+←/→ kelime atla · "
    "Home/End · Ctrl+U/Ctrl+K satırı sil · ↑/↓ önceki girdiler · shift+tab mod · alt+v resim"
)


def _enable_ctrl_backspace() -> None:
    """Windows konsolunda Ctrl+Backspace'i 'önceki kelimeyi sil' yapar.

    Win32 girdi okuyucu Backspace'i 0x08, Ctrl+Backspace'i 0x7f olarak alır ama
    ikisini de aynı tuşa (c-h) eşler; 0x7f'yi Ctrl+W'ye (unix-word-rubout)
    yönlendiriyoruz. Yalnız Windows; diğer platformlarda 0x7f düz Backspace'tir.
    """
    if sys.platform != "win32":
        return
    try:
        from prompt_toolkit.input.win32 import ConsoleInputReader
        from prompt_toolkit.key_binding.key_processor import KeyPress
        from prompt_toolkit.keys import Keys
    except Exception:  # noqa: BLE001 — kozmetik; olmazsa Backspace yine çalışır
        return
    if getattr(ConsoleInputReader, "_kuzgun_ctrl_backspace", False):
        return
    orig = ConsoleInputReader._event_to_key_presses
    ctrl_mask = ConsoleInputReader.LEFT_CTRL_PRESSED | ConsoleInputReader.RIGHT_CTRL_PRESSED
    vk_back = 0x08

    def patched(self, ev):
        if ev.ControlKeyState & ctrl_mask and (
            ev.VirtualKeyCode == vk_back or ev.uChar.UnicodeChar in ("\x08", "\x7f")
        ):
            return [KeyPress(Keys.ControlW, "")]  # Ctrl+Backspace → önceki kelimeyi sil
        return orig(self, ev)

    ConsoleInputReader._event_to_key_presses = patched
    ConsoleInputReader._kuzgun_ctrl_backspace = True


def make_session(state: dict, commands=None, arg_choices=None, needs_arg=None, **session_kwargs):
    """Durum satırlı prompt_toolkit oturumu.

    shift+tab modu döndürür; alt+v pano resmini ekler (state['attachments']);
    Ctrl+C çalışan işi iptal eder; `commands` verilirse '/' menüsü açılır.
    session_kwargs (input=/output=) test içindir.
    """
    from prompt_toolkit import PromptSession
    from prompt_toolkit.application import get_app
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.shortcuts import CompleteStyle
    from prompt_toolkit.styles import Style

    state.setdefault("attachments", [])
    state.setdefault("queue", [])
    state.setdefault("busy", None)
    _enable_ctrl_backspace()
    kb = KeyBindings()

    @kb.add("s-tab")
    def _(event):
        toggle_mode(state)
        event.app.invalidate()  # durum satırı hemen yenilensin

    @kb.add("escape", "v")  # alt+v
    def _(event):
        grab = state.get("grab")
        if grab is None:
            from kuzgun.vision import grab_clipboard_image

            def grab():
                return grab_clipboard_image(state.get("images_dir") or "data/images")

        path = grab()
        if not path:
            state["flash"] = "panoda resim yok"
            return
        state["attachments"].append(path)
        event.current_buffer.insert_text(f"[resim {len(state['attachments'])}] ")

    def _cancel_running() -> bool:
        """Çalışan iş varsa iptal bayrağını kaldırır (adımlar arasında durur). True döner."""
        if state.get("busy"):
            cancel = state.get("cancel")
            if cancel is not None:
                cancel.set()
            state["busy"] = "İptal ediliyor…"
            return True
        return False

    @kb.add("c-c")
    def _(event):
        if _cancel_running():
            return
        if event.current_buffer.text:
            event.current_buffer.reset()
            return
        event.app.exit(exception=KeyboardInterrupt())

    @kb.add("escape")  # ESC: Claude gibi çalışan işi iptal et; boştaysa satırı temizle
    def _(event):
        if not _cancel_running():
            event.current_buffer.reset()

    def toolbar():
        mode = state["mode"]
        color = _ANSI[MODE_COLORS.get(mode, "green")]
        try:
            cols = get_app().output.get_size().columns
        except Exception:  # noqa: BLE001
            cols = 0
        rule = "─" * max((cols or _width()) - 1, 20)  # -1: satır sarmasın
        parts = [f"<b><style fg='{color}'>▶▶ {mode} mod</style></b><dim> (shift+tab)</dim>"]
        if state.get("busy"):
            frame = _SPINNER[int(time.time() * 10) % len(_SPINNER)]
            parts.append(f"<style fg='ansimagenta'>{frame} {state['busy']}</style><dim> (Ctrl+C iptal)</dim>")
        if state["queue"]:
            parts.append(f"<dim>⏳ sırada {len(state['queue'])} mesaj</dim>")
        if state["attachments"]:
            parts.append(f"<dim>🖼 {len(state['attachments'])} resim ekli</dim>")
        if state.get("flash"):
            parts.append(f"<style fg='ansiyellow'>{state.pop('flash')}</style>")
        return HTML(f"<rule>{rule}</rule>\n  " + "<dim> · </dim>".join(parts))

    style = Style.from_dict(
        {
            "bottom-toolbar": "noreverse",
            "bottom-toolbar.text": "noreverse",
            "rule": "ansibrightblack",
            "dim": "ansibrightblack",
            "prompt": "ansimagenta bold",
            "placeholder": "ansibrightblack italic",
            # '/' menüsü: koyu zemin, seçili satır vurgulu, açıklama soluk
            "completion-menu": "bg:#1c1c1c #d0d0d0",
            "completion-menu.completion": "bg:#1c1c1c #d0d0d0",
            "completion-menu.completion.current": "bg:#5f5faf #ffffff bold",
            "completion-menu.meta.completion": "bg:#1c1c1c #808080",
            "completion-menu.meta.completion.current": "bg:#5f5faf #e0e0e0",
        }
    )
    completer = SlashCompleter(commands, arg_choices, needs_arg) if commands else None
    return PromptSession(
        message=[("class:prompt", "❯ ")],
        placeholder=[("class:placeholder", _HINT)],
        bottom_toolbar=toolbar,
        key_bindings=kb,
        style=style,
        completer=completer,
        complete_while_typing=True,  # '/' yazar yazmaz menü açılsın
        complete_style=CompleteStyle.COLUMN,  # tek sütun: komut + açıklama
        erase_when_done=True,  # gönderilen satırı biz basarız (print_user)
        refresh_interval=0.1,  # dönen simge
        **session_kwargs,
    )


def set_title(title: str, file=None) -> None:
    """Terminal sekme/pencere başlığını ayarlar (OSC 0; Windows Terminal, xterm…).
    Claude Code gibi: başlık konuşmanın adı/ilk mesajı olur."""
    import re

    clean = re.sub(r"[\x00-\x1f\x7f]", "", title)
    out = file if file is not None else sys.__stdout__  # patch_stdout proxysini atla
    try:
        out.write(f"\x1b]0;{clean}\x07")
        out.flush()
    except Exception:  # noqa: BLE001 — başlık kozmetik; hata sohbeti durdurmasın
        pass


def print_rule(console) -> None:
    console.print("─" * max(console.width - 1, 20), style="bright_black")


def confirm_in_terminal(fn):
    """İşçi iş parçacığından, çalışan prompt'u geçici olarak askıya alıp
    terminalde input() kullanan bir onay fonksiyonu çalıştırır."""
    loop = _LOOP
    if loop is None or not loop.is_running():
        return fn()
    from prompt_toolkit.application import run_in_terminal

    async def _run():
        return await run_in_terminal(fn)

    return asyncio.run_coroutine_threadsafe(_run(), loop).result()


async def run_interactive(state: dict, console, handle, session_kwargs=None, **session_opts) -> None:
    """Sabit girdi kutusu + kuyruk döngüsü.

    handle(text, images, cancel_event) her mesaj için ayrı iş parçacığında
    çalışır ve çıktısını console ile basar (patch_stdout kutunun üstüne yazar).
    Kutu meşgulken gelen mesajlar sıraya alınır, sırayla işlenir.
    """
    global _LOOP
    from prompt_toolkit.patch_stdout import patch_stdout

    _LOOP = asyncio.get_running_loop()
    session = make_session(state, **session_opts, **(session_kwargs or {}))
    worker: asyncio.Task | None = None

    def start(item):
        nonlocal worker
        text, images = item
        cancel = threading.Event()
        state["cancel"] = cancel
        state["busy"] = "Düşünüyor…"

        async def job():
            nonlocal worker
            try:
                await asyncio.to_thread(handle, text, images, cancel)
            finally:
                state["busy"] = None
                if state.get("quit"):  # /cikis → kutuyu kapat, döngü bitsin
                    state["queue"].clear()
                    worker = None
                    if session.app.is_running:
                        session.app.exit(exception=EOFError())
                elif state["queue"]:
                    start(state["queue"].pop(0))
                else:
                    worker = None

        worker = asyncio.get_running_loop().create_task(job())

    with patch_stdout(raw=True):
        while True:
            try:
                text = await session.prompt_async()
            except (EOFError, KeyboardInterrupt):
                break
            images = list(state["attachments"])
            state["attachments"] = []
            text = text.replace("﻿", "").strip()
            if not text and not images:
                continue
            print_user(console, text, images)
            if state.get("busy"):
                state["queue"].append((text, images))
                console.print("  [dim]⏳ sıraya alındı[/]")
            else:
                start((text, images))
        # Çıkışta süren iş varsa (iptal edilmemişse) bitmesini bekle.
        while worker is not None and not worker.done():
            await asyncio.sleep(0.05)
    _LOOP = None


def run_plain(state: dict, console, handle) -> None:
    """Terminal değilken (boru/test): eş zamanlı, düz input() döngüsü."""
    while True:
        console.print(f"\n[bold cyan]\\[{state['mode']}] sen>[/] ", end="")
        try:
            text = input().replace("﻿", "").strip()  # olası BOM'u temizle
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        handle(text, [], threading.Event())
        if state.get("quit"):
            break
