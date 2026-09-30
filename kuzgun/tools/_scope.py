"""Güvenlik araçları için hedef kapsam koruması.

İki kontrol:
- SSRF: iç/özel/loopback ağ adreslerini engelle (web içeriği modeli kandırıp iç
  ağa yöneltmesin).
- Yetki: KUZGUN_SCAN_ALLOWLIST verilmişse yalnız o domain(ler) taranabilir; aktif
  tarama (security_scan) için allowlist ZORUNLU (yetkisiz/kandırılmış hedefi engeller).
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def parse_host(target: str) -> str | None:
    t = target if "://" in target else "https://" + target
    return urlparse(t).hostname


def _default_resolve(host: str) -> list[str]:
    try:
        return [ai[4][0] for ai in socket.getaddrinfo(host, None)]
    except Exception:
        return []


def is_private_host(host: str, _resolve=None) -> bool:
    """Host bir iç/özel/loopback/link-local adrese çözülüyorsa True (güvensiz)."""
    if not host:
        return True
    resolve = _resolve or _default_resolve
    try:
        ipaddress.ip_address(host)
        ips = [host]
    except ValueError:
        ips = resolve(host)
    if not ips:
        return True  # çözülemiyor → güvenli tarafta kal
    for ip in ips:
        try:
            a = ipaddress.ip_address(ip)
        except ValueError:
            return True
        if a.is_private or a.is_loopback or a.is_link_local or a.is_reserved or a.is_multicast:
            return True
    return False


def check_scope(target: str, allowlist: str = "", require_allowlist: bool = False, _resolve=None):
    """(izin_var_mı, red_sebebi) döner. SSRF + (varsa/gerekiyorsa) allowlist denetimi."""
    host = parse_host(target)
    if not host:
        return False, "geçersiz hedef adresi."
    if is_private_host(host, _resolve=_resolve):
        return False, f"iç/özel ağ adresi taranamaz (SSRF koruması): {host}"
    allow = [h.strip().lower() for h in (allowlist or "").split(",") if h.strip()]
    if allow:
        low = host.lower()
        if not any(low == a or low.endswith("." + a) for a in allow):
            return False, f"yetkisiz hedef: {host}. İzinli: {', '.join(allow)}"
    elif require_allowlist:
        return False, (
            "Yetkili hedef listesi ayarlı değil. Aktif tarama için KUZGUN_SCAN_ALLOWLIST "
            "ortam değişkenine kendi domainini yaz (ör. ahmetyuceler.com.tr) ve tekrar dene."
        )
    return True, None
