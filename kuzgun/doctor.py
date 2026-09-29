"""Sağlık kontrolü (Faz C9) — `kuzgun-doctor`.

Kuzgun'un çalışması için gereken her şeyi deterministik olarak kontrol eder: Ollama
erişimi, gerekli modellerin inmiş olması, `claude` CLI, hafıza DB'sinin yazılabilirliği,
MCP config. Problar enjekte edilebilir (test için). Model zekâsı KULLANILMAZ.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

from kuzgun.config import Config, load_config


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def _list_ollama_models(config: Config) -> list[str]:
    """Ollama'nın indirilmiş modellerini listeler (/api/tags). Hata olursa []"""
    import json
    import urllib.request

    base = config.ollama_url.rsplit("/v1", 1)[0]  # .../v1 -> kök
    try:
        with urllib.request.urlopen(base + "/api/tags", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        return []


def check_ollama(config: Config) -> tuple[bool, str]:
    models = _list_ollama_models(config)
    if models:
        return True, f"erişilebilir ({len(models)} model indirilmiş)"
    return False, f"erişilemedi ({config.ollama_url}) — Ollama çalışıyor mu?"


def check_models(config: Config, available: list[str] | None = None) -> tuple[bool, str]:
    if available is None:
        available = _list_ollama_models(config)
    # Ollama adları 'qwen2.5:7b-instruct' gibi; kısmi eşleşmeye de izin ver.
    def has(name: str) -> bool:
        return any(name == a or a.startswith(name) or name.startswith(a.split(":")[0]) for a in available)

    need = {config.model, config.coder_model, config.embed_model, config.vision_model}
    missing = sorted(n for n in need if not has(n))
    if missing:
        return False, "eksik model(ler): " + ", ".join(missing) + " (ollama pull ...)"
    return True, "gerekli modeller mevcut"


def check_claude(_which=None) -> tuple[bool, str]:
    which = _which or (lambda n: shutil.which(n))
    path = which("claude") or which("claude.cmd")
    if path:
        return True, f"bulundu: {path}"
    return False, "claude CLI PATH'te yok — devretme/uzman danışma çalışmaz"


def check_db(db_path: str) -> tuple[bool, str]:
    if db_path == ":memory:":
        return True, "bellek-içi (geçici)"
    try:
        parent = os.path.dirname(db_path) or "."
        os.makedirs(parent, exist_ok=True)
        probe = os.path.join(parent, ".kuzgun-yazma-testi")
        with open(probe, "w") as f:
            f.write("x")
        os.remove(probe)
        return True, f"yazılabilir: {db_path}"
    except Exception as exc:
        return False, f"yazılamıyor ({db_path}): {exc}"


def check_mcp(config: Config) -> tuple[bool, str]:
    if os.path.isfile(config.mcp_config_path):
        return True, f"MCP config var: {config.mcp_config_path}"
    return True, "MCP config yok (opsiyonel)"


_DEFAULT_PROBES = {
    "ollama": check_ollama,
    "models": check_models,
    "claude": lambda cfg: check_claude(),
    "db": lambda cfg: check_db(cfg.db_path),
    "mcp": check_mcp,
}


def run_checks(config: Config, probes: dict | None = None) -> list[Check]:
    probes = probes if probes is not None else _DEFAULT_PROBES
    checks = []
    for name, fn in probes.items():
        try:
            ok, detail = fn(config)
        except Exception as exc:  # noqa: BLE001 — kontrol kendi çökmesin
            ok, detail = False, f"kontrol hatası: {exc}"
        checks.append(Check(name, ok, detail))
    return checks


def format_report(checks: list[Check]) -> str:
    lines = ["Kuzgun sağlık kontrolü:"]
    for c in checks:
        lines.append(f"  {'✓' if c.ok else '✗'} {c.name}: {c.detail}")
    n_ok = sum(1 for c in checks if c.ok)
    lines.append(f"\n{n_ok}/{len(checks)} kontrol geçti.")
    return "\n".join(lines)


def main() -> None:  # kuzgun-doctor giriş noktası
    report = format_report(run_checks(load_config()))
    print(report)


if __name__ == "__main__":
    main()
