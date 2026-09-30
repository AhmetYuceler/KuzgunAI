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

    out = security_scan("https://ahmetyuceler.com.tr", _run=fake_run, _which=lambda n: "nuclei.exe")
    assert "CVE-2023-1234" in out
    assert "high" in out.lower()
    assert "2" in out  # bulgu sayısı


def test_no_findings():
    out = security_scan("https://x", _run=lambda cmd, timeout: (0, "", ""),
                        _which=lambda n: "nuclei.exe")
    assert "bulgu" in out.lower()


def test_missing_nuclei_gives_install_hint():
    # nuclei kurulu değilse: Kuzgun'un kendi kurabilmesi için yol gösteren mesaj.
    out = security_scan("https://x", _run=None, _which=lambda n: None)
    assert "nuclei" in out.lower()
    assert "kur" in out.lower()  # kurulum ipucu


def test_target_required():
    assert security_scan("", _which=lambda n: "nuclei.exe").startswith("Error:")
