from __future__ import annotations

import os

from kuzgun import __version__
from kuzgun.analyze import is_init_intent
from kuzgun.engine import (  # build_default_registry/inject_memory: testlerce içe aktarılır
    SYSTEM_PROMPT,
    KuzgunEngine,
    build_default_registry,
    inject_memory,
)
from kuzgun.permissions import MODES

# B8: komut tablosu + taşıma-bağımsız komut işleme ortak repl.py'de (yerel + HTTP paylaşır).
# Testlerce `kuzgun.cli`'den içe aktarıldıkları için burada re-export edilir.
from kuzgun.repl import (
    _NEEDS_ARG,
    COMMAND_HELP,
    COMMANDS,
    format_history,
    handle_slash,
)
from kuzgun.teacher import ask_claude

__all__ = [
    "main", "handle_slash", "format_history", "COMMANDS", "COMMAND_HELP",
    "build_default_registry", "inject_memory", "SYSTEM_PROMPT",
]


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


def session_title(meta: dict, limit: int = 50) -> str:
    """Sekme başlığı: oturum adı > ilk mesaj > 'Kuzgun' (Claude Code'un başlığı gibi)."""
    text = (meta.get("name") or meta.get("title") or "").strip()
    if not text:
        return "Kuzgun"
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def resume_session(engine, archive, arg: str, state: dict) -> str:
    """/resume [ad|id|no]: oturumu geri yükler (engine.messages değişir).

    Argümansızsa numaralı liste döner; kullanıcı `/resume <no>` yazar (kutu
    açıkken araya modal input() sokmak tuşları ikiye böldüğü için seçim ayrı
    komutla yapılır). Sistem promptu GÜNCEL tutulur; yalnız konuşma geri gelir."""
    from kuzgun.archive import title_for

    key = (arg or "").strip()
    cwd = state.get("cwd")
    # Claude Code gibi proje bazlı: önce bu klasörün oturumları; '/resume hepsi' tümü.
    metas = archive.list(cwd=cwd) if cwd and key != "hepsi" else []
    scope = "Bu klasörün oturumları"
    if not metas:
        metas = archive.list()
        scope = "Tüm oturumlar"
    if not metas:
        return "Kayıtlı oturum yok."
    if not key or key == "hepsi":
        ipucu = " · diğer klasörler için: /resume hepsi" if scope.startswith("Bu") else ""
        return (
            f"{scope} (dönmek için: /resume <no> ya da /resume <ad>{ipucu}):\n"
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
    from kuzgun import ui

    ui.set_title(session_title(meta))
    return (
        f"Oturuma dönüldü: {etiket} ({meta.get('turns', 0)} tur). "
        f"Son konuşma:\n{format_history(engine.messages, n=4)}"
    )


_PROJECT_HEADER = "[Proje haritası —"


def init_command(engine, root: str, state: dict, progress=None) -> str:
    """/init: projeyi tara → parça parça özetlet → KUZGUN.md yaz → bağlama al.
    Model çağrısı araçsız tek tur (engine.client.chat)."""
    from kuzgun.analyze import init_project, load_project_notes
    from kuzgun.models import AssistantMessage

    def model_fn(prompt: str) -> str:
        out = engine.client.chat([{"role": "user", "content": prompt}], None)
        return out.text or "" if isinstance(out, AssistantMessage) else str(out)

    _, report = init_project(root, model_fn, progress=progress)
    notes = load_project_notes(root)
    ctx = f"{_PROJECT_HEADER} {root}\\KUZGUN.md]\n{notes}" if notes else None
    engine.extra_context = ctx  # yeni oturumlar için
    # Süren konuşmaya da hemen gir: eski harita notu varsa yerine koy, yoksa ekle.
    msgs = engine.messages
    for i, m in enumerate(msgs):
        if m.get("role") == "system" and str(m.get("content", "")).startswith(_PROJECT_HEADER):
            if ctx:
                msgs[i] = {"role": "system", "content": ctx}
            else:
                del msgs[i]
            break
    else:
        if ctx:
            msgs.insert(1, {"role": "system", "content": ctx})
    state["project_loaded"] = True
    return report


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
    import atexit

    from rich.console import Console
    from rich.panel import Panel

    from kuzgun import ui, vision
    from kuzgun.analyze import load_project_notes
    from kuzgun.archive import SessionArchive

    args = _parse_args(argv)
    console = Console()
    # Çalışma klasöründeki KUZGUN.md (/init çıktısı) her oturumda bağlama girer.
    proje_notu = load_project_notes(os.getcwd())
    extra = f"{_PROJECT_HEADER} {os.getcwd()}\\KUZGUN.md]\n{proje_notu}" if proje_notu else None
    engine = KuzgunEngine(confirm=_confirm, extra_context=extra)
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
        "cwd": os.getcwd(),  # /resume ve --continue bu klasörün oturumlarını önceler
    }
    ui.set_title("Kuzgun")
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
            # Sekme başlığı konuşmayı yansıtsın (ad varsa ad, yoksa ilk mesaj).
            ui.set_title(session_title(archive.load(state["session_id"])[1]))
        except Exception as exc:  # noqa: BLE001 — arşiv hatası sohbeti durdurmasın
            console.print(f"[dim]arşiv uyarısı: {exc}[/]")

    # Başlangıçta devam: --continue (en son) ya da --resume [ad]
    if args.cont or args.resume is not None:
        key = args.resume or ""
        if args.cont:
            son = archive.latest(cwd=os.getcwd()) or archive.latest()
            key = son["id"] if son else "yok"
        ui.print_note(console, resume_session(engine, archive, key, state))

    def _sor(user: str, images: list[str], cancel) -> None:
        """Bir kullanıcı mesajını modele iletir; iptal edilmediyse cevabı basar.
        on_step ile alt durum barı canlı 'ne yapıyor' gösterir (Claude Code gibi)."""
        cevap = run_guarded(
            engine.chat, user, mode=state["mode"], images=images or None,
            on_step=lambda m: state.__setitem__("busy", m),
        )
        if cancel.is_set():
            return
        ui.print_reply(console, cevap)

    def handle(user: str, images: list[str], cancel) -> None:
        """Tek bir girdiyi (slash komutu ya da mesaj) işler ve çıktısını basar.
        Etkileşimli kutuda ayrı iş parçacığında çalışır; kutu altta kalır."""
        if user == "/gecmis":
            console.print(Panel(format_history(engine.messages), title="Geçmiş", border_style="dim"))
            return
        if user == "/doktor":
            from kuzgun.doctor import format_report, run_checks

            state["busy"] = "sağlık kontrolü…"
            rapor = run_guarded(lambda: format_report(run_checks(engine.config)))
            console.print(Panel(rapor, title="Sağlık Kontrolü", border_style="dim"))
            return
        if user == "/fork":
            # Konuşmayı çatalla: mevcut hâli arşive yaz, kopyasını yeni oturuma al,
            # aktif oturumu yeni kopyaya çevir (orijinal arşivde kalır).
            _save()
            yeni = archive.new_id()
            archive.save(yeni, engine.messages, mode=state["mode"], cwd=os.getcwd())
            state["session_id"] = yeni
            ui.print_note(console, "Konuşma çatallandı; kopyada devam ediyorsun (orijinal arşivde).")
            return
        if user in ("/init", "/analiz") or (not user.startswith("/") and is_init_intent(user)):
            root = os.getcwd()
            console.print(f"  [dim]proje taranıyor: {root}[/]")

            def _prog(msg: str) -> None:
                state["busy"] = f"/init: {msg}"

            cevap = run_guarded(init_command, engine, root, state, progress=_prog)
            if not cancel.is_set():
                ui.print_note(console, cevap, style="green")
            return
        if user == "/resume" or user.startswith("/resume "):
            ui.print_note(console, resume_session(engine, archive, user[7:].strip(), state))
            return
        if user.startswith("/rename "):
            ad = user[len("/rename ") :].strip()
            _save()
            archive.rename(state["session_id"], ad)
            ui.set_title(ad)
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

        def _resume_choices():
            # '/resume ' sonrası: ad (varsa) ya da numara; yanında ilk mesaj
            metas = archive.list(cwd=os.getcwd()) or archive.list()
            return [(m["name"] or str(i), m.get("title", "")) for i, m in enumerate(metas, 1)] + [
                ("hepsi", "diğer klasörlerdeki oturumlar")
            ]

        asyncio.run(
            ui.run_interactive(
                state,
                console,
                handle,
                commands=COMMAND_HELP,
                arg_choices={"/mod": lambda: list(MODES), "/resume": _resume_choices},
                needs_arg=set(_NEEDS_ARG) | {"/mod", "/resume"},
            )
        )
    else:
        ui.run_plain(state, console, handle)


if __name__ == "__main__":
    main()
