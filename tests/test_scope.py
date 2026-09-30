"""Güvenlik hedef kapsam koruması (SSRF + allowlist)."""

from __future__ import annotations

from kuzgun.tools._scope import check_scope, is_private_host, parse_host


def test_parse_host():
    assert parse_host("https://ahmetyuceler.com.tr/a") == "ahmetyuceler.com.tr"
    assert parse_host("ahmetyuceler.com.tr") == "ahmetyuceler.com.tr"


def test_private_ips_blocked():
    for ip in ("127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.1.1", "::1"):
        assert is_private_host(ip) is True


def test_public_ip_allowed():
    assert is_private_host("8.8.8.8") is False


def test_check_scope_blocks_internal():
    ok, reason = check_scope("http://192.168.1.10")
    assert ok is False and "SSRF" in reason


def test_check_scope_allowlist_enforced():
    # allowlist verildiğinde yalnız o domain (ve alt alan adları).
    resolve = lambda h: ["8.8.8.8"]  # public çöz
    ok, _ = check_scope("https://ahmetyuceler.com.tr", allowlist="ahmetyuceler.com.tr", _resolve=resolve)
    assert ok is True
    ok2, r2 = check_scope("https://baskasite.com", allowlist="ahmetyuceler.com.tr", _resolve=resolve)
    assert ok2 is False and "yetkisiz" in r2.lower()
    # alt alan adı da izinli
    ok3, _ = check_scope("https://api.ahmetyuceler.com.tr", allowlist="ahmetyuceler.com.tr", _resolve=resolve)
    assert ok3 is True


def test_require_allowlist_refuses_when_empty():
    resolve = lambda h: ["8.8.8.8"]
    ok, reason = check_scope("https://x.com", allowlist="", require_allowlist=True, _resolve=resolve)
    assert ok is False and "KUZGUN_SCAN_ALLOWLIST" in reason


def test_no_allowlist_allows_public_when_not_required():
    resolve = lambda h: ["8.8.8.8"]
    ok, _ = check_scope("https://x.com", allowlist="", require_allowlist=False, _resolve=resolve)
    assert ok is True
