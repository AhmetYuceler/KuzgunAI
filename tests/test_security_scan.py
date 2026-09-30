"""security_scan: nuclei ile gerçek zafiyet taraması (yetkili hedef)."""

from __future__ import annotations

from kuzgun.tools.security_scan import SECURITY_SCAN_SCHEMA, security_scan


def test_schema_name():
    assert SECURITY_SCAN_SCHEMA["function"]["name"] == "security_scan"


def test_reports_findings_from_nuclei():
    def fake_run(cmd, timeout):
        # nuclei -silent tarzı çıktı
        out = ("[tls-version] [ssl] [info] https://x\n"
               "[CVE-2023-1234] [http] [high] https://x/login\n")
        return 0, out, ""

    out = security_scan("https://ahmetyuceler.com.tr", _run=fake_run, _which=lambda n: "nuclei.exe", _scope=lambda t: (True, None))
    assert "CVE-2023-1234" in out
    assert "high" in out.lower()
    assert "2" in out  # bulgu sayısı


def test_no_findings():
    out = security_scan("https://x", _run=lambda cmd, timeout: (0, "", ""),
                        _which=lambda n: "nuclei.exe", _scope=lambda t: (True, None))
    assert "bulgu" in out.lower()


def test_missing_nuclei_gives_install_hint():
    # nuclei kurulu değilse: Kuzgun'un kendi kurabilmesi için yol gösteren mesaj.
    out = security_scan("https://x", _run=None, _which=lambda n: None, _scope=lambda t: (True, None))
    assert "nuclei" in out.lower()
    assert "kur" in out.lower()  # kurulum ipucu


def test_target_required():
    assert security_scan("", _which=lambda n: "nuclei.exe").startswith("Error:")


def test_security_scan_requires_authorized_target():
    # Yetki/SSRF: yetkisiz ya da çözülemeyen hedefte aktif tarama REDDEDİLMELİ.
    out = security_scan("https://baskasite.com", _run=lambda c, t: (0, "", ""),
                        _which=lambda n: "nuclei.exe")
    assert out.startswith("Error:")
    assert "KUZGUN_SCAN_ALLOWLIST" in out or "SSRF" in out or "yetkisiz" in out.lower()


def test_security_scan_allowlist_permits_authorized():
    # allowlist enjekte edilmiş kapsamla yetkili hedef geçmeli.
    out = security_scan("https://ahmetyuceler.com.tr",
                        _run=lambda c, t: (0, "[x] [http] [low] u", ""),
                        _which=lambda n: "nuclei.exe",
                        _scope=lambda t: __import__("kuzgun.tools._scope", fromlist=["check_scope"]).check_scope(
                            t, "ahmetyuceler.com.tr", require_allowlist=True, _resolve=lambda h: ["8.8.8.8"]))
    assert not out.startswith("Error:")
