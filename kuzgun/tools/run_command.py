from __future__ import annotations

import subprocess
import sys

RUN_COMMAND_SCHEMA = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": (
            "Bir kabuk (shell) komutu çalıştırır ve çıktısını döndürür. Script "
            "çalıştırmak, derlemek, test etmek veya sistem bilgisi almak için kullan. "
            "Kalıcı değişiklik yapabilir; dikkatli kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Çalıştırılacak komut."},
                "timeout": {
                    "type": "integer",
                    "description": "Saniye cinsinden zaman aşımı. Varsayılan 30.",
                },
            },
            "required": ["command"],
        },
    },
}


def _kill_tree(proc: subprocess.Popen) -> None:
    """Süreci ve tüm alt süreçlerini öldürür.

    Windows'ta ``shell=True`` ile cmd.exe'yi öldürmek torun süreçleri (ör. ping)
    öldürmez; ``taskkill /T`` tüm ağacı sonlandırır.
    """
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
        )
    else:
        proc.kill()


def run_command(command: str, timeout: int = 30) -> str:
    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        return f"Error: komut {timeout} saniyede zaman aşımına uğradı."
    parts = []
    if (stdout or "").strip():
        parts.append(stdout.strip())
    if (stderr or "").strip():
        parts.append(f"[stderr]\n{stderr.strip()}")
    if proc.returncode != 0:
        parts.append(f"[çıkış kodu {proc.returncode}]")
    return "\n".join(parts)
