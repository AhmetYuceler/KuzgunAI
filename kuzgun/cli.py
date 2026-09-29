from __future__ import annotations

import difflib
import os

from kuzgun import __version__
from kuzgun.engine import (  # build_default_registry/inject_memory: testlerce içe aktarılır
    KuzgunEngine,
    SYSTEM_PROMPT,
    build_default_registry,
    inject_memory,
)
from kuzgun.permissions import MODES
from kuzgun.teacher import ask_claude


# Argümansız yazılırsa kullanım gösterilen komutlar (argümanlısı main() içinde işlenir).
_NEEDS_ARG = {"/hatirla": "<şey>", "/ajanlar": "<görev>", "/claude": "<soru>"}
COMMANDS = (
    "/yardim", "/mod", "/plan", "/normal", "/otonom", "/claude", "/ajanlar",
    "/hatirla", "/notlar", "/gecmis", "/cikis",
)


def handle_slash(line: str, state: dict) -> str | None:
    """Slash komutunu işler. Slash değilse None döner."""
    if not line.startswith("/"):
        return None
    parts = line.split()
    cmd = parts[0]
    if cmd in ("/cikis", "/exit", "/quit"):
        state["quit"] = True
        return "Görüşürüz!"
    if cmd == "/yardim":
        return (
            "Komutlar: /mod <plan|normal|otonom> (ya da kısaca /plan, /normal, /otonom; "
            "shift+tab de döndürür), /claude <soru> (uzmana danış), "
            "/ajanlar <görev> (çok adımlı işi böl-yap), /hatirla <şey>, /notlar, "
            "/gecmis, /yardim, /cikis"
        )
    if cmd == "/mod":
        if len(parts) < 2:
            return f"Şu anki mod: {state['mode']}. Kullanım: /mod {'|'.join(MODES)}"
        yeni = parts[1]
        if yeni not in MODES:
            return f"Geçersiz mod: {yeni}. Seçenekler: {', '.join(MODES)}"
        state["mode"] = yeni
        return f"Mod değişti: {yeni}"
    if cmd[1:] in MODES:  # /plan <görev> → moda geç, görev varsa hemen işle
        state["mode"] = cmd[1:]
        gorev = line[len(cmd) :].strip()
        if gorev:
            state["pending"] = gorev
        return f"Mod değişti: {state['mode']}"
    if cmd in _NEEDS_ARG and len(parts) < 2:
        return f"Kullanım: {cmd} {_NEEDS_ARG[cmd]}"
    yakin = difflib.get_close_matches(cmd, COMMANDS, n=1, cutoff=0.6)
    ipucu = f" Şunu mu demek istedin: {yakin[0]}?" if yakin else ""
    return f"Bilinmeyen komut: {cmd}.{ipucu} /yardim yaz."


def format_history(messages: list[dict], n: int = 8) -> str:
    """Son n kullanıcı/asistan turunu okunabilir metne çevirir (sistem hariç)."""
    turns = [m for m in messages if m.get("role") in ("user", "assistant")]
    recent = turns[-n:]
    if not recent:
        return "Geçmiş boş."
    lines = []
    for m in recent:
        who = "sen" if m["role"] == "user" else "kuzgun"
        content = (m.get("content", "") or "").strip().replace("\n", " ")
        lines.append(f"[{who}] {content[:200]}")
    return "\n".join(lines)


def run_guarded(fn, *args, **kwargs) -> str:
    """Uzun işi (model/claude/ajanlar) çalıştırır; Ctrl+C'de traceback yerine
    kısa bir iptal mesajı, hatada '[hata] ...' döner. Program kapanmaz."""
    try:
        return fn(*args, **kwargs)
    except KeyboardInterrupt:
        return "[iptal edildi]"
    except Exception as exc:  # noqa: BLE001
        return f"[hata] {exc}"


def _confirm(name: str, arguments: dict) -> bool:
    print(f"\n[onay] Kuzgun '{name}' çalıştırmak istiyor: {arguments}")
    ans = input("İzin veriyor musun? (e/h) ").strip().lower()
    return ans in ("e", "evet", "y", "yes")


def main() -> None:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel

    from kuzgun import ui

    console = Console()
    engine = KuzgunEngine(confirm=_confirm)
    state = {"mode": engine.config.mode, "quit": False}  # başlangıç modu (KUZGUN_MODE)
    console.print()
    console.print(
        ui.render_header(
            version=__version__, model=engine.config.model, cwd=ui.short_path(os.getcwd())
        )
    )
    console.print()
    session = ui.make_session(state) if ui.is_interactive() else None

    def _sor(user: str) -> None:
        """Bir kullanıcı mesajını modele iletir ve cevabı basar."""
        console.print("[dim]düşünüyor... (Ctrl+C iptal)[/]")
        cevap = run_guarded(engine.chat, user, mode=state["mode"])
        console.print("[bold green]kuzgun>[/]")
        console.print(Markdown(cevap))

    while True:
        try:
            user = ui.read_input(state, console, session)
        except (EOFError, KeyboardInterrupt):
            break
        if not user:
            continue
        if user == "/gecmis":
            console.print(Panel(format_history(engine.messages), title="Geçmiş", border_style="dim"))
            continue
        if user == "/notlar":
            from kuzgun.notebook import load_notes

            notlar = load_notes(engine.config.notes_path) or "Henüz kalıcı not yok."
            console.print(Panel(notlar, title="Kalıcı Notlar (KUZGUN.md)", border_style="dim"))
            continue
        if user.startswith("/hatirla "):
            from kuzgun.notebook import load_notes
            from kuzgun.tools.remember import remember

            sonuc = remember(user[len("/hatirla ") :].strip(), _path=engine.config.notes_path)
            engine.notes = load_notes(engine.config.notes_path)  # sonraki turda bağlama girer
            console.print(f"[yellow]{sonuc}[/]")
            continue
        if user.startswith("/ajanlar "):
            gorev = user[len("/ajanlar ") :].strip()
            console.print("[dim]ajanlar çalışıyor: görev bölünüyor ve tek tek yapılıyor... (Ctrl+C iptal)[/]")
            cevap = run_guarded(engine.run_agents, gorev, mode=state["mode"], confirm=_confirm)
            console.print("[bold green]ajanlar>[/]")
            console.print(Markdown(cevap))
            continue
        if user.startswith("/claude "):
            soru = user[len("/claude ") :].strip()
            # Son konuşmayı da gönder: 'üstteki hataları düzelt' gibi sorular anlaşılsın.
            baglam = format_history(engine.messages, n=6)
            if baglam == "Geçmiş boş.":
                baglam = ""
            with console.status("[dim]Claude'a danışılıyor... (Ctrl+C iptal)[/]"):
                cevap = run_guarded(ask_claude, soru, context=baglam)
            console.print("[bold magenta]claude>[/]")
            console.print(Markdown(cevap))
            if cevap and not cevap.startswith(("Error:", "[")):
                try:
                    engine.memory.add(soru, cevap, engine.embedder)
                except Exception:
                    pass
            continue
        slash = handle_slash(user, state)
        if slash is not None:
            console.print(f"[yellow]{slash}[/]")
            if state["quit"]:
                break
            pending = state.pop("pending", None)
            if pending:  # '/plan <görev>' → mod değişti, şimdi görevi işle
                _sor(pending)
            continue
        _sor(user)


if __name__ == "__main__":
    main()
