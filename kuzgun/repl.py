"""Ortak REPL çekirdeği (Faz B8).

Komut tablosu ve taşıma-BAĞIMSIZ komut işleme burada tek yerde tanımlıdır; hem yerel
`kuzgun` (cli.py) hem HTTP ince istemcisi (client.py) buradan kullanır — böylece
komutlar iki yerde tekrar edilmez. Yalnız her ikisi için de anlamlı komutlar (mod,
yardım, çıkış) burada; yerele özgü zengin komutlar (/init, /resume, /ajanlar…) cli.py'de.
"""

from __future__ import annotations

import difflib

from kuzgun.permissions import MODES

_EDIT_KEYS_HELP = (
    "Kısayollar: Ctrl+Backspace/Ctrl+Delete kelime sil · Ctrl+←/→ kelime atla · "
    "Home/End · Ctrl+U/Ctrl+K satırı sil · ↑/↓ önceki girdiler · shift+tab mod · alt+v resim"
)

# Argümansız yazılırsa kullanım gösterilen komutlar (argümanlısı cli.py içinde işlenir).
_NEEDS_ARG = {
    "/hatirla": "<şey>",
    "/ajanlar": "<görev>",
    "/claude": "<soru>",
    "/rename": "<ad>",
}
COMMANDS = (
    "/yardim", "/init", "/mod", "/plan", "/normal", "/otonom", "/claude", "/ajanlar",
    "/hatirla", "/notlar", "/gecmis", "/resume", "/rename", "/cikis",
)
# '/' menüsünde komutun yanında soluk görünen açıklamalar (Claude Code'daki gibi).
COMMAND_HELP = {
    "/yardim": "komutları listele",
    "/init": "projeyi analiz et, KUZGUN.md oluştur (her oturumda yüklenir)",
    "/mod": "mod değiştir: plan | normal | otonom",
    "/plan": "plan moduna geç (değişiklik yapmaz); görev de verilebilir",
    "/normal": "normal moda geç (değişiklikte onay sorar)",
    "/otonom": "otonom moda geç (onaysız çalışır)",
    "/claude": "uzmana (Claude) danış",
    "/ajanlar": "görevi böl, alt-ajanlarla tek tek yap",
    "/hatirla": "kalıcı not al (KUZGUN.md)",
    "/notlar": "kalıcı notları göster",
    "/gecmis": "bu oturumun son konuşmasını göster",
    "/resume": "eski bir oturuma dön",
    "/rename": "bu oturuma ad ver",
    "/cikis": "Kuzgun'dan çık",
}


def handle_slash(line: str, state: dict) -> str | None:
    """Taşıma-bağımsız slash komutlarını işler (mod/yardım/çıkış). Slash değilse None."""
    if not line.startswith("/"):
        return None
    parts = line.split()
    cmd = parts[0]
    if cmd in ("/cikis", "/exit", "/quit"):
        state["quit"] = True
        return "Görüşürüz!"
    if cmd == "/yardim":
        return (
            "Komutlar: /init (projeyi analiz et → KUZGUN.md), "
            "/mod <plan|normal|otonom> (ya da kısaca /plan, /normal, /otonom; "
            "shift+tab de döndürür), /claude <soru> (uzmana danış), "
            "/ajanlar <görev> (çok adımlı işi böl-yap), /hatirla <şey>, /notlar, "
            "/gecmis, /resume [ad|no] (eski oturuma dön), /rename <ad> (oturuma ad ver), "
            "/yardim, /cikis\n" + _EDIT_KEYS_HELP
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
