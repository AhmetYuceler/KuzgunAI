from __future__ import annotations

from kuzgun.engine import (  # build_default_registry/inject_memory: testlerce içe aktarılır
    KuzgunEngine,
    SYSTEM_PROMPT,
    build_default_registry,
    inject_memory,
)
from kuzgun.permissions import MODES
from kuzgun.teacher import ask_claude


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
            "Komutlar: /mod <plan|normal|otonom>, /claude <soru> (uzmana danış), "
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
    return f"Bilinmeyen komut: {cmd}. /yardim yaz."


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


def _confirm(name: str, arguments: dict) -> bool:
    print(f"\n[onay] Kuzgun '{name}' çalıştırmak istiyor: {arguments}")
    ans = input("İzin veriyor musun? (e/h) ").strip().lower()
    return ans in ("e", "evet", "y", "yes")


def main() -> None:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel

    console = Console()
    engine = KuzgunEngine(confirm=_confirm)
    state = {"mode": "normal", "quit": False}
    console.print(
        Panel.fit(
            "[bold]🦅 Kuzgun[/] hazır — kişisel yerel yapay zekâ ajanın\n"
            "[dim]/yardim · /mod · /claude · /gecmis · /cikis[/]",
            border_style="cyan",
        )
    )
    while True:
        # Girişi düz input() ile alıyoruz (rich console.input non-tty/pipe'ta sorunlu).
        console.print(f"\n[bold cyan]\\[{state['mode']}] sen>[/] ", end="")
        try:
            user = input().replace("﻿", "").strip()  # olası BOM'u temizle
        except (EOFError, KeyboardInterrupt):
            break
        if not user:
            continue
        if user == "/gecmis":
            console.print(Panel(format_history(engine.messages), title="Geçmiş", border_style="dim"))
            continue
        if user.startswith("/claude "):
            soru = user[len("/claude ") :].strip()
            with console.status("[dim]Claude'a danışılıyor...[/]"):
                cevap = ask_claude(soru)
            console.print("[bold magenta]claude>[/]")
            console.print(Markdown(cevap))
            if cevap and not cevap.startswith("Error:"):
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
            continue
        console.print("[dim]düşünüyor...[/]")
        try:
            cevap = engine.chat(user, mode=state["mode"])
        except Exception as exc:
            cevap = f"[hata] {exc}"
        console.print("[bold green]kuzgun>[/]")
        console.print(Markdown(cevap))


if __name__ == "__main__":
    main()
