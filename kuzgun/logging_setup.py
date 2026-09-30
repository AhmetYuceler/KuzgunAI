"""Loglama altyapısı (Faz B1).

Tüm Kuzgun modülleri `kuzgun.<modül>` altında logger kullanır. Sessiz `except`
blokları yerine buradan alınan logger'a yazılır; böylece bir şey ters gidince
iz kalır. `timed` bağlam yöneticisi bir işlemin süresini (ms) loglar — model
çağrısı ve araç çalıştırması başına süreli satır için.
"""

from __future__ import annotations

import contextlib
import logging
import sys
import time
from collections.abc import Iterator

_ROOT = "kuzgun"
_configured = False


def get_logger(name: str | None = None) -> logging.Logger:
    """`kuzgun` ya da `kuzgun.<name>` logger'ını döndürür."""
    return logging.getLogger(_ROOT if not name else f"{_ROOT}.{name}")


def setup_logging(
    level: str | int = "INFO", log_file: str | None = None, console: bool = True
) -> None:
    """Kök `kuzgun` logger'ını yapılandırır. Idempotent: ikinci çağrı handler
    çoğaltmaz (sadece seviyeyi günceller).

    `console=False`: ekrana (stderr) yazma; yalnız dosyaya yaz. Etkileşimli TUI'de
    stderr'e INFO akıtmak sabit kutuyu bozar — o yüzden TUI dosyaya yazar, ekranda
    zaten canlı adım günlüğü var. Hiç handler kalmasın diye NullHandler eklenir."""
    global _configured
    root = logging.getLogger(_ROOT)
    lvl = logging.getLevelName(level) if isinstance(level, str) else level
    root.setLevel(lvl)
    if _configured:
        for h in root.handlers:
            h.setLevel(lvl)
        return
    fmt = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s", "%H:%M:%S")
    if console:
        ch = logging.StreamHandler(sys.stderr)
        ch.setFormatter(fmt)
        ch.setLevel(lvl)
        root.addHandler(ch)
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        fh.setLevel(lvl)
        root.addHandler(fh)
    if not root.handlers:
        root.addHandler(logging.NullHandler())  # propagate=False + handler yok → uyarı basmasın
    root.propagate = False
    _configured = True


@contextlib.contextmanager
def timed(log: logging.Logger, what: str, level: int = logging.INFO, **fields) -> Iterator[None]:
    """`what` işleminin süresini ms olarak loglar. Ek alanlar `k=v` biçiminde eklenir.
    İşlem hata verse de süre (hata bilgisiyle) loglanır."""
    t0 = time.perf_counter()
    extra = (" " + " ".join(f"{k}={v}" for k, v in fields.items())) if fields else ""
    try:
        yield
    except Exception as exc:  # noqa: BLE001 — sadece logla, sonra yeniden fırlat
        dt = (time.perf_counter() - t0) * 1000
        log.log(level, "%s HATA %.0fms%s: %s", what, dt, extra, exc)
        raise
    else:
        dt = (time.perf_counter() - t0) * 1000
        log.log(level, "%s %.0fms%s", what, dt, extra)
