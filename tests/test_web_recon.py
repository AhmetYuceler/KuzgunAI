"""web_recon: gerçek HTTP/teknoloji parmak izi (yetkili güvenlik testi)."""

from __future__ import annotations

from kuzgun.tools.web_recon import WEB_RECON_SCHEMA, _fingerprint, web_recon


def test_schema_name():
    assert WEB_RECON_SCHEMA["function"]["name"] == "web_recon"


def test_fingerprint_detects_wordpress_php():
    headers = {"server": "Apache", "x-powered-by": "PHP/8.1", "set-cookie": "PHPSESSID=abc; wordpress_test_cookie=1"}
    html = '<meta name="generator" content="WordPress 6.4" /> <link href="/wp-content/themes/x">'
    techs = _fingerprint(headers, html)
    assert "PHP" in techs
    assert "WordPress" in techs
    assert "Apache" in techs


def test_fingerprint_detects_aspnet():
    headers = {"x-powered-by": "ASP.NET", "x-aspnet-version": "4.0", "set-cookie": "ASP.NET_SessionId=x"}
    techs = _fingerprint(headers, "")
    assert "ASP.NET" in techs


def test_web_recon_reports_headers_and_tech():
    def fake_fetch(url):
        if url.endswith("/robots.txt"):
            return 200, {}, "User-agent: *\nDisallow: /admin"
        # kök ve yol probları
        status = 200 if url.rstrip("/").endswith("ahmetyuceler.com.tr") else 404
        headers = {"server": "nginx", "x-powered-by": "PHP/8.2",
                   "set-cookie": "laravel_session=z", "content-type": "text/html"}
        return status, headers, "<html><meta name=generator content='Laravel'></html>"

    out = web_recon("https://ahmetyuceler.com.tr", _fetch=fake_fetch)
    assert "nginx" in out
    assert "PHP" in out
    assert "Laravel" in out
    assert "robots.txt" in out.lower()


def test_web_recon_flags_missing_security_headers():
    def fake_fetch(url):
        return 200, {"server": "nginx"}, "<html></html>"  # güvenlik başlıkları yok

    out = web_recon("https://x.example", _fetch=fake_fetch)
    # CSP/HSTS gibi eksik başlıklar rapora 'eksik' olarak girmeli
    assert "eksik" in out.lower() or "yok" in out.lower()


def test_web_recon_error_caught():
    def boom(url):
        raise RuntimeError("bağlantı yok")

    assert web_recon("https://x", _fetch=boom).startswith("Error:")
