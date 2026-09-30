"""web_recon: yetkili güvenlik testi için gerçek HTTP/teknoloji keşfi.

Bir hedef URL'ye GERÇEKTEN istek atar (kurulu araç gerekmez; httpx/ssl/socket):
- HTTP durum + başlıklar (Server, X-Powered-By, çerezler, güvenlik başlıkları)
- Teknoloji parmak izi (PHP/WordPress/Laravel/ASP.NET/Django/… başlık+çerez+HTML'den)
- TLS sertifika özeti
- robots.txt ve yaygın hassas yolların (/admin, /.git, /.env, /wp-login.php…) varlığı

Yalnız KEŞİF yapar (GET), hedefi değiştirmez. Sonucu, Kuzgun'un bir sonraki adımda
(nuclei/sqlmap gibi) kullanabileceği kısa bir rapora çevirir.
"""

from __future__ import annotations

WEB_RECON_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_recon",
        "description": (
            "Bir web hedefinde (yetkili güvenlik testi) GERÇEK keşif yapar: HTTP "
            "başlıkları, kullanılan teknolojiler (sunucu/dil/CMS/framework), TLS "
            "sertifikası, güvenlik başlıkları ve yaygın hassas yolların varlığı. "
            "Bir siteyi 'ne kullanıyor' diye incelemek için İLK adım budur."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Hedef URL (https://site)."}
            },
            "required": ["url"],
        },
    },
}

_SEC_HEADERS = (
    "content-security-policy",
    "strict-transport-security",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
)

_PROBE_PATHS = (
    "/robots.txt", "/sitemap.xml", "/.well-known/security.txt",
    "/admin", "/administrator", "/wp-login.php", "/wp-admin/",
    "/.git/HEAD", "/.env", "/phpinfo.php", "/server-status",
    "/config.php.bak", "/backup.zip", "/.htaccess",
)

# (imza, teknoloji) — başlık/çerez/HTML metninde küçük harf arama.
_SIGNS = (
    ("php", "PHP"), ("phpsessid", "PHP"),
    ("wordpress", "WordPress"), ("wp-content", "WordPress"), ("wp-includes", "WordPress"),
    ("laravel", "Laravel"), ("laravel_session", "Laravel"),
    ("asp.net", "ASP.NET"), ("asp.net_sessionid", "ASP.NET"), ("x-aspnet", "ASP.NET"),
    ("django", "Django"), ("csrftoken", "Django"),
    ("jsessionid", "Java"), ("express", "Express/Node"),
    ("drupal", "Drupal"), ("joomla", "Joomla"),
    ("cloudflare", "Cloudflare"), ("nginx", "nginx"), ("apache", "Apache"),
    ("react", "React"), ("vue", "Vue"), ("next.js", "Next.js"),
)


def _fingerprint(headers: dict, html: str) -> list[str]:
    """Başlık + çerez + HTML'den kullanılan teknolojileri çıkarır."""
    hay = " ".join(f"{k}:{v}" for k, v in headers.items()).lower() + " " + (html or "").lower()
    found = []
    for sign, tech in _SIGNS:
        if sign in hay and tech not in found:
            found.append(tech)
    # 'server' başlığındaki değeri de doğrudan ekle (ör. 'LiteSpeed').
    srv = headers.get("server", "")
    if srv:
        token = srv.split("/")[0].split()[0]
        if token and token not in found and len(token) > 1:
            found.append(token)
    return found


def _default_fetch(url: str):
    import httpx

    # verify=False BİLİNÇLİ: bu bir keşif aracı; test edilen hedefin sertifikası
    # geçersiz/self-signed olsa bile bağlanıp incelemek gerekir. Sertifika
    # GEÇERLİLİĞİ ayrıca _default_tls (doğrulamalı) tarafından rapor edilir.
    r = httpx.get(url, timeout=8, follow_redirects=True, verify=False)  # noqa: S501
    return r.status_code, {k.lower(): v for k, v in r.headers.items()}, r.text[:20000]


def _default_tls(host: str) -> str:
    import socket
    import ssl

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=6) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                cert = ss.getpeercert()
        issuer = dict(x[0] for x in cert.get("issuer", [])).get("organizationName", "?")
        exp = cert.get("notAfter", "?")
        sans = ", ".join(v for k, v in cert.get("subjectAltName", []) if k == "DNS")[:200]
        return f"veren={issuer}, bitiş={exp}, alan adları={sans}"
    except Exception as exc:  # noqa: BLE001
        return f"(TLS bilgisi alınamadı: {exc})"


def web_recon(url: str, _fetch=None, _tls=None, _allowlist: str = "", _scope=None) -> str:
    fetch = _fetch or _default_fetch
    testing = _fetch is not None  # enjekte fetch → test/kontrollü: gerçek TLS'e gitme
    # SSRF koruması: iç/özel ağ adreslerini engelle (allowlist opsiyonel — keşif hafif).
    from kuzgun.tools._scope import check_scope

    scope = _scope or (lambda t: check_scope(t, _allowlist, require_allowlist=False))
    ok, reason = scope(url)
    if not ok:
        return f"Error: {reason}"
    try:
        from urllib.parse import urlparse

        base = url.rstrip("/")
        host = urlparse(base if "://" in base else "https://" + base).hostname or base
        status, headers, html = fetch(base)
        techs = _fingerprint(headers, html)

        lines = [f"# Keşif raporu: {base}", f"HTTP durum: {status}"]
        srv = headers.get("server", "?")
        xpb = headers.get("x-powered-by", "")
        lines.append(f"Sunucu: {srv}" + (f" · X-Powered-By: {xpb}" if xpb else ""))
        lines.append("Teknolojiler: " + (", ".join(techs) if techs else "belirlenemedi"))
        cookies = headers.get("set-cookie", "")
        if cookies:
            lines.append(f"Çerezler: {cookies[:200]}")

        eksik = [h for h in _SEC_HEADERS if h not in headers]
        lines.append("Eksik güvenlik başlıkları: " + (", ".join(eksik) if eksik else "yok (iyi)"))

        if _tls is not None:
            lines.append(f"TLS: {_tls(host)}")
        elif not testing:
            lines.append(f"TLS: {_default_tls(host)}")

        # Yaygın hassas yolları prob et (404 olmayanlar ilginç).
        bulunan = []
        for path in _PROBE_PATHS:
            try:
                st, _, _ = fetch(base + path)
                if st and st != 404:
                    bulunan.append(f"{path} [{st}]")
            except Exception:  # noqa: BLE001 — tek yol hatası taramayı durdurmasın
                continue
        lines.append("Erişilebilir yollar: " + (", ".join(bulunan) if bulunan else "yaygın yol bulunamadı"))
        lines.append(
            "\nSonraki adım önerisi: teknolojilere göre 'security_scan' aracıyla "
            "nuclei/sqlmap ile bilinen zafiyetleri test et."
        )
        return "\n".join(lines)
    except Exception as exc:  # noqa: BLE001
        return f"Error: web_recon başarısız: {exc}"
