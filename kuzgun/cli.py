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
    return f"Bilinmeyen komut: {cmd}. /yardim yaz."


def _confirm(name: str, arguments: dict) -> bool:
    print(f"\n[onay] Kuzgun '{name}' çalıştırmak istiyor: {arguments}")
    ans = input("İzin veriyor musun? (e/h) ").strip().lower()
    return ans in ("e", "evet", "y", "yes")


def main() -> None:
    # Tek çekirdek: motor. CLI etkileşimli onayı sağlar; hafıza/araç/döngü motorda.
    engine = KuzgunEngine(confirm=_confirm)
    state = {"mode": "normal", "quit": False}
    print(f"Kuzgun hazır (mod: {state['mode']}). /yardim ile komutlar, /cikis ile çık.")
    while True:
        try:
            user = input(f"\n[{state['mode']}] sen> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user:
            continue
        if user.startswith("/claude "):
            soru = user[len("/claude ") :].strip()
            cevap = ask_claude(soru)
            print(f"\n[claude] {cevap}")
            if cevap and not cevap.startswith("Error:"):  # hataları öğrenme
                try:
                    engine.memory.add(soru, cevap, engine.embedder)
                except Exception:
                    pass
            continue
        slash = handle_slash(user, state)
        if slash is not None:
            print(slash)
            if state["quit"]:
                break
            continue
        try:
            cevap = engine.chat(user, mode=state["mode"])
        except Exception as exc:
            cevap = f"[hata] {exc}"
        print(f"\nkuzgun> {cevap}")


if __name__ == "__main__":
    main()
