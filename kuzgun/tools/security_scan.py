"""security_scan: yetkili hedefte nuclei ile GERÇEK zafiyet/CVE taraması.

`web_recon` ile teknoloji tespit edildikten sonra bilinen zafiyetleri test etmek
için kullanılır. nuclei'yi (kuruluysa) çalıştırır, bulguları özetler. nuclei kurulu
değilse Kuzgun'un kendisinin kurabilmesi için yol gösteren bir mesaj döner.

Yalnız YETKİLİ hedeflerde (kendi siten) kullan. Varsayılan şablonlar yıkıcı değildir
(zafiyeti tespit eder, tahrip etmez).
"""

from __future__ import annotations

import os
import shutil

SECURITY_SCAN_SCHEMA = {
    "type": "function",
    "function": {
        "name": "security_scan",
        "description": (
            "Yetkili bir web hedefinde (kendi siten) nuclei ile bilinen zafiyet/CVE "
            "taraması yapar ve bulguları döndürür. 'exploit/zafiyet var mı' sorusunu "
            "GERÇEKTEN test eder. Önce web_recon ile keşif yapmak iyi olur."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Hedef URL (kendi siten)."},
                "severity": {
                    "type": "string",
                    "description": "Önem süzgeci, ör. 'medium,high,critical'. Varsayılan hepsi.",
                },
            },
            "required": ["target"],
        },
    },
}


def _find_nuclei() -> str | None:
    """nuclei'yi PATH'te ya da bilinen yerlerde (KUZGUN_SECTOOLS, ./sectools) bulur."""
    p = shutil.which("nuclei") or shutil.which("nuclei.exe")
    if p:
        return p
    for base in (os.environ.get("KUZGUN_SECTOOLS", ""), "sectools",
                 os.path.join(os.path.dirname(__file__), "..", "..", "sectools")):
        if not base:
            continue
        cand = os.path.join(base, "nuclei.exe")
        if os.path.isfile(cand):
            return cand
        cand = os.path.join(base, "nuclei")
        if os.path.isfile(cand):
            return cand
    return None


def _default_run(cmd: list, timeout: int):
    import subprocess

    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
        encoding="utf-8", errors="replace",
    )
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def security_scan(target: str, severity: str = "", _run=None, _which=None,
                  _allowlist: str = "", _scope=None) -> str:
    if not target or not target.strip():
        return "Error: hedef (target) gerekli."
    # Yetki + SSRF: aktif tarama yalnız allowlist'teki (yetkili) hedeflerde.
    from kuzgun.tools._scope import check_scope

    scope = _scope or (lambda t: check_scope(t, _allowlist, require_allowlist=True))
    ok, reason = scope(target.strip())
    if not ok:
        return f"Error: {reason}"
    find = _which or (lambda n: _find_nuclei())
    nuclei = find("nuclei")
    if not nuclei:
        return (
            "nuclei kurulu değil. Bu aracı kullanabilmek için nuclei'yi KUR: "
            "ProjectDiscovery nuclei Windows sürümünü indirip (GitHub releases, "
            "nuclei_*_windows_amd64.zip) sectools klasörüne çıkar ya da PATH'e ekle. "
            "Kurduktan sonra tekrar dene."
        )
    run = _run or _default_run
    cmd = [nuclei, "-u", target.strip(), "-silent",
           "-severity", severity.strip() or "info,low,medium,high,critical",
           "-timeout", "6", "-rate-limit", "100"]
    try:
        code, out, err = run(cmd, 600)  # en çok 10 dk
    except Exception as exc:  # noqa: BLE001 (zaman aşımı vb.)
        return f"security_scan: nuclei çalışırken sorun/zaman aşımı: {exc}"
    findings = [ln for ln in (out or "").splitlines() if ln.strip().startswith("[")]
    if not findings:
        note = f" (nuclei uyarısı: {err.strip()[:200]})" if err.strip() else ""
        return f"Tarama bitti: bilinen zafiyet BULGUSU yok.{note}"
    başlık = f"Tarama bitti: {len(findings)} bulgu (nuclei):"
    return başlık + "\n" + "\n".join(findings[:100])
