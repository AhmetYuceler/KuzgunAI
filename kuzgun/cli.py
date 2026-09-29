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
_NEEDS_ARG = {
    "/hatirla": "<şey>",
    "/ajanlar": "<görev>",
    "/claude": "<soru>",
    "/rename": "<ad>",
}
COMMANDS = (
    "/yardim", "/mod", "/plan", "/normal", "/otonom", "/claude", "/ajanlar",
    "/hatirla", "/notlar", "/gecmis", "/resume", "/rename", "/cikis",
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
            "/gecmis, /resume [ad|no] (eski oturuma dön), /rename <ad> (oturuma ad ver), "
            "/yardim, /cikis"
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


def format_session_list(metas: list[dict]) -> str:
    """/resume listesi: no, ad/başlık, tarih, tur sayısı (Claude Code seçicisi gibi)."""
    import time

    if not metas:
        return "Kayıtlı oturum yok."
    lines = []
    for i, m in enumerate(metas, 1):
        when = time.strftime("%d.%m %H:%M", time.localtime(m.get("updated", 0)))
        ad = f"{m['name']}  —  " if m.get("name") else ""
        lines.append(f"{i:>2}. {ad}{m.get('title', '')}  [dim]({when} · {m.get('turns', 0)} tur)[/]")
    return "\n".join(lines)


def resume_session(engine, archive, arg: str, state: dict) -> str:
    """/resume [ad|id|no]: oturumu geri yükler (engine.messages değişir).

    Argümansızsa numaralı liste döner; kullanıcı `/resume <no>` yazar (kutu
    açıkken araya modal input() sokmak tuşları ikiye böldüğü için seçim ayrı
    komutla yapılır). Sistem promptu GÜNCEL tutulur; yalnız konuşma geri gelir."""
    from kuzgun.archive import title_for

    metas = archive.list()
    if not metas:
        return "Kayıtlı oturum yok."
    key = (arg or "").strip()
    if not key:
        return (
            "Kayıtlı oturumlar (dönmek için: /resume <no> ya da /resume <ad>):\n"
            + format_session_list(metas)
        )
    if key.isdigit() and 1 <= int(key) <= len(metas):
        meta = metas[int(key) - 1]
    else:
        meta = archive.find(key)
    if meta is None:
        return f"Oturum bulunamadı: {key}. /resume ile listeden seç."
    messages, meta = archive.load(meta["id"])
    if messages and messages[0].get("role") == "system":
        messages = messages[1:]
    engine.messages[:] = [engine.messages[0]] + messages  # sistem promptu güncel
    state["session_id"] = meta["id"]
    if meta.get("mode") in MODES:
        state["mode"] = meta["mode"]
    etiket = meta.get("name") or title_for(engine.messages)
    return (
        f"Oturuma dönüldü: {etiket} ({meta.get('turns', 0)} tur). "
        f"Son konuşma:\n{format_history(engine.messages, n=4)}"
    )


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
    """Normal modda değişiklik yapan araç için onay. Etkileşimli kutu açıkken
    prompt geçici askıya alınır (ui.confirm_in_terminal), yoksa düz input()."""
    from kuzgun import ui

    def ask() -> bool:
        print(f"\n[onay] Kuzgun '{name}' çalıştırmak istiyor: {arguments}")
        ans = input("İzin veriyor musun? (e/h) ").strip().lower()
        return ans in ("e", "evet", "y", "yes")

    return ui.confirm_in_terminal(ask)


def _parse_args(argv=None):
    import argparse

    ap = argparse.ArgumentParser(prog="kuzgun", description="Kişisel yerel yapay zekâ ajanı")
    ap.add_argument(
        "-c", "--continue", dest="cont", action="store_true", help="en son oturuma devam et"
    )
    ap.add_argument(
        "-r", "--resume", nargs="?", const="", default=None, metavar="AD",
        help="oturuma dön: ad/id ver ya da boş bırakıp listeden seç",
    )
    ap.add_argument("-n", "--name", default="", help="bu oturuma ad ver")
    return ap.parse_args(argv)


def main(argv=None) -> None:
    from rich.console import Console
    from rich.panel import Panel

    from kuzgun import ui

    import atexit

    from kuzgun import vision
    from kuzgun.archive import SessionArchive

    args = _parse_args(argv)
    console = Console()
    engine = KuzgunEngine(confirm=_confirm)
    # /resume arşivi: her turdan sonra konuşma diske yazılır; eskiler süpürülür.
    archive = SessionArchive(engine.config.sessions_dir)
    archive.sweep(engine.config.session_days)
    # alt+v resimleri: kalıcı klasör verilmediyse oturumluk geçici klasör, çıkışta
    # (/cikis, Ctrl+C, Ctrl+D) silinir; eski oturumlardan kalanlar süpürülür.
    images_dir = engine.config.images_dir
    if not images_dir:
        vision.sweep_stale()
        images_dir = vision.new_session_dir()
        atexit.register(vision.cleanup_session_dir, images_dir)
    state = {
        "mode": engine.config.mode,
        "quit": False,
        "images_dir": images_dir,
        "session_id": archive.new_id(),
    }
    console.print()
    console.print(
        ui.render_header(
            version=__version__, model=engine.config.model, cwd=ui.short_path(os.getcwd())
        )
    )
    console.print()

    def _save() -> None:
        try:
            archive.save(state["session_id"], engine.messages, mode=state["mode"], cwd=os.getcwd())
            if args.name:
                archive.rename(state["session_id"], args.name)
        except Exception as exc:  # noqa: BLE001 — arşiv hatası sohbeti durdurmasın
            console.print(f"[dim]arşiv uyarısı: {exc}[/]")

    # Başlangıçta devam: --continue (en son) ya da --resume [ad]
    if args.cont or args.resume is not None:
        key = args.resume or ""
        if args.cont:
            son = archive.latest()
            key = son["id"] if son else "yok"
        ui.print_note(console, resume_session(engine, archive, key, state))

    def _sor(user: str, images: list[str], cancel) -> None:
        """Bir kullanıcı mesajını modele iletir; iptal edilmediyse cevabı basar."""
        cevap = run_guarded(engine.chat, user, mode=state["mode"], images=images or None)
        if cancel.is_set():
            return
        ui.print_reply(console, cevap)

    def handle(user: str, images: list[str], cancel) -> None:
        """Tek bir girdiyi (slash komutu ya da mesaj) işler ve çıktısını basar.
        Etkileşimli kutuda ayrı iş parçacığında çalışır; kutu altta kalır."""
        if user == "/gecmis":
            console.print(Panel(format_history(engine.messages), title="Geçmiş", border_style="dim"))
            return
        if user == "/resume" or user.startswith("/resume "):
            ui.print_note(console, resume_session(engine, archive, user[7:].strip(), state))
            return
        if user.startswith("/rename "):
            ad = user[len("/rename ") :].strip()
            _save()
            archive.rename(state["session_id"], ad)
            ui.print_note(console, f"Oturum adı: {ad}")
            return
        if user == "/notlar":
            from kuzgun.notebook import load_notes

            notlar = load_notes(engine.config.notes_path) or "Henüz kalıcı not yok."
            console.print(Panel(notlar, title="Kalıcı Notlar (KUZGUN.md)", border_style="dim"))
            return
        if user.startswith("/hatirla "):
            from kuzgun.notebook import load_notes
            from kuzgun.tools.remember import remember

            sonuc = remember(user[len("/hatirla ") :].strip(), _path=engine.config.notes_path)
            engine.notes = load_notes(engine.config.notes_path)  # sonraki turda bağlama girer
            ui.print_note(console, sonuc)
            return
        if user.startswith("/ajanlar "):
            gorev = user[len("/ajanlar ") :].strip()
            state["busy"] = "Ajanlar çalışıyor: görev bölünüyor…"
            cevap = run_guarded(engine.run_agents, gorev, mode=state["mode"], confirm=_confirm)
            if not cancel.is_set():
                ui.print_reply(console, cevap, who="ajanlar")
            return
        if user.startswith("/claude "):
            soru = user[len("/claude ") :].strip()
            # Son konuşmayı da gönder: 'üstteki hataları düzelt' gibi sorular anlaşılsın.
            baglam = format_history(engine.messages, n=6)
            if baglam == "Geçmiş boş.":
                baglam = ""
            state["busy"] = "Claude'a danışılıyor…"
            cevap = run_guarded(ask_claude, soru, context=baglam)
            if cancel.is_set():
                return
            ui.print_reply(console, cevap, who="claude")
            if cevap and not cevap.startswith(("Error:", "[")):
                try:
                    engine.memory.add(soru, cevap, engine.embedder)
                except Exception:
                    pass
            return
        slash = handle_slash(user, state)
        if slash is not None:
            ui.print_note(console, slash)
            if state["quit"]:
                return
            pending = state.pop("pending", None)
            if pending:  # '/plan <görev>' → mod değişti, şimdi görevi işle
                _sor(pending, images, cancel)
                _save()
            return
        _sor(user, images, cancel)
        _save()  # her turdan sonra arşive yaz (/resume için)

    if ui.is_interactive():
        import asyncio

        asyncio.run(ui.run_interactive(state, console, handle))
    else:
        ui.run_plain(state, console, handle)


if __name__ == "__main__":
    main()
