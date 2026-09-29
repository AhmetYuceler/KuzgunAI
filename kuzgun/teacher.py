from __future__ import annotations

import os
import shutil
import subprocess


def _default_runner(question: str) -> str:
    """`claude` CLI'ı etkileşimsiz (--print) çağırır ve cevabı döndürür.

    Kullanıcının Claude Max üyeliğiyle çalışır; ayrı API anahtarı gerekmez.

    Güvenlik: (a) soru argv yerine stdin'den verilir → argüman enjeksiyonu olmaz;
    (b) geçerli dizindeki bir 'claude' çalıştırılmaz → Windows yol-kaçırma koruması.
    """
    from kuzgun.config import load_config

    exe = shutil.which("claude.cmd") or shutil.which("claude")
    if not exe:
        return "Error: 'claude' komutu bulunamadı."
    exe_abs = os.path.abspath(exe)
    cwd = os.getcwd()
    if exe_abs == cwd or exe_abs.startswith(cwd + os.sep):
        return "Error: güvenlik: geçerli dizindeki 'claude' çalıştırılmaz."
    proc = subprocess.run(
        [exe_abs, "--print"],
        input=question,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=load_config().claude_timeout,  # KUZGUN_CLAUDE_TIMEOUT ile ayarlanır
    )
    if proc.returncode != 0:
        return f"Error: claude hata verdi: {(proc.stderr or '').strip()[:300]}"
    return proc.stdout.strip()


def ask_claude(question: str, _runner=None, context: str = "") -> str:
    """Bir soruyu danışman Claude'a sorar ve cevabını döndürür.

    `context`: Kuzgun'daki son konuşma; 'üstteki hataları düzelt' gibi sorularda
    Claude neyin kastedildiğini görsün diye sorunun önüne eklenir.
    Hata durumunda (claude yok, zaman aşımı, boş soru) 'Error: ...' döner.
    """
    if not question or not question.strip():
        return "Error: boş soru."
    prompt = question.strip()
    if context and context.strip():
        prompt = (
            "[Bağlam: kullanıcının yerel asistanı Kuzgun ile son konuşması]\n"
            f"{context.strip()}\n\n[Kullanıcının sana sorusu]\n{prompt}"
        )
    runner = _runner or _default_runner
    try:
        return runner(prompt)
    except subprocess.TimeoutExpired as exc:
        return (
            f"Error: claude {int(exc.timeout)} sn içinde cevap vermedi (zaman aşımı). "
            "Uzun işler için KUZGUN_CLAUDE_TIMEOUT değerini artırabilirsin."
        )
    except Exception as exc:
        return f"Error: {exc}"
