from __future__ import annotations

import shutil
import subprocess


def _default_runner(question: str) -> str:
    """`claude` CLI'ı etkileşimsiz (--print) çağırır ve cevabı döndürür.

    Kullanıcının Claude Max üyeliğiyle çalışır; ayrı API anahtarı gerekmez.
    """
    exe = shutil.which("claude.cmd") or shutil.which("claude")
    if not exe:
        return "Error: 'claude' komutu bulunamadı."
    proc = subprocess.run(
        [exe, "--print", question],
        capture_output=True,
        text=True,
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
