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
        timeout=180,
    )
    if proc.returncode != 0:
        return f"Error: claude hata verdi: {(proc.stderr or '').strip()[:300]}"
    return proc.stdout.strip()


def ask_claude(question: str, _runner=None) -> str:
    """Bir soruyu danışman Claude'a sorar ve cevabını döndürür.

    Hata durumunda (claude yok, zaman aşımı, boş soru) 'Error: ...' döner.
    """
    if not question or not question.strip():
        return "Error: boş soru."
    runner = _runner or _default_runner
    try:
        return runner(question.strip())
    except Exception as exc:
        return f"Error: {exc}"
