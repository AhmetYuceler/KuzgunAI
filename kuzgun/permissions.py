from __future__ import annotations

from typing import Callable

MODES = ("plan", "normal", "otonom")


def is_allowed(
    name: str,
    arguments: dict,
    mutating: bool,
    mode: str,
    confirm: Callable[[str, dict], bool] | None = None,
) -> tuple[bool, str | None]:
    """Bir araç çağrısına moda göre izin verilip verilmeyeceğine karar verir.

    Dönüş: (izin_var_mı, izin_yoksa_gerekçe_mesajı).

    Okuyan araçlar ve otonom mod serbest. Değişiklik yapan araçlarda:
    - normal mod: kullanıcıya onay sorulur;
    - plan modu ve TANINMAYAN modlar: en kısıtlayıcı davranış — engellenir.
    """
    if not mutating or mode == "otonom":
        return True, None
    if mode == "normal":
        approved = bool(confirm(name, arguments)) if confirm else False
        if approved:
            return True, None
        return False, f"[reddedildi] '{name}' için izin verilmedi."
    # plan modu veya tanınmayan mod -> güvenli varsayılan: engelle
    etiket = "plan modu" if mode == "plan" else f"'{mode}' modu (tanınmıyor)"
    return False, (
        f"[{etiket}] '{name}' değişiklik yapan bir araç; çalıştırılmadı. "
        "Uygulamak için: /mod normal"
    )
