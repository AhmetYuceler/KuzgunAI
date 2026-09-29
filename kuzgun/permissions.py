from __future__ import annotations

import fnmatch
import re
from collections.abc import Callable
from dataclasses import dataclass

MODES = ("plan", "normal", "otonom")

# İzin kuralı sözdizimi: "<eylem> <araç>[(<param>:<glob>)]"
#   allow run_command(cmd:git *)      → 'git ...' komutlarına sorusuz izin
#   deny  write_file(path:*Windows*)  → Windows yoluna yazmayı engelle
#   ask   run_command(cmd:*)          → her komutta onay sor
#   deny  run_command                 → aracı tümüyle engelle (param'sız)
_RULE_RE = re.compile(
    r"^\s*(allow|deny|ask)\s+([A-Za-z0-9_]+)\s*(?:\(\s*([A-Za-z0-9_]+)\s*:\s*(.*?)\s*\)\s*)?$"
)


@dataclass(frozen=True)
class Rule:
    action: str  # allow | deny | ask
    tool: str
    param: str | None = None
    pattern: str | None = None


def parse_rules(text: str) -> list[Rule]:
    """Kural metnini (satır ya da ';' ile ayrık) Rule listesine çevirir. Geçersiz
    satırlar sessizce atlanır (yanlış kural yüzünden başlatma çökmesin)."""
    rules: list[Rule] = []
    for chunk in re.split(r"[\n;]+", text or ""):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = _RULE_RE.match(chunk)
        if not m:
            continue
        action, tool, param, pattern = m.groups()
        rules.append(Rule(action, tool, param, pattern))
    return rules


def _rule_matches(rule: Rule, name: str, arguments: dict) -> bool:
    if rule.tool != name:
        return False
    if rule.param is None:
        return True
    value = str(arguments.get(rule.param, ""))
    return fnmatch.fnmatch(value, rule.pattern or "*")


def evaluate_rules(rules, name: str, arguments: dict) -> str | None:
    """Eşleşen kurala göre 'deny' | 'allow' | 'ask' döner; hiçbiri eşleşmezse None.
    Öncelik: deny > allow > ask (en kısıtlayıcı kazanır)."""
    matched = [r.action for r in rules if _rule_matches(r, name, arguments)]
    for action in ("deny", "allow", "ask"):
        if action in matched:
            return action
    return None


def is_allowed(
    name: str,
    arguments: dict,
    mutating: bool,
    mode: str,
    confirm: Callable[[str, dict], bool] | None = None,
    rules=(),
) -> tuple[bool, str | None]:
    """Bir araç çağrısına izin verilip verilmeyeceğine karar verir.

    Dönüş: (izin_var_mı, izin_yoksa_gerekçe_mesajı).

    Önce kural tablosu (C5) uygulanır (mod'dan bağımsız, deterministik):
    deny → engelle; allow → izin; ask → onaya sor. Kural yoksa mod mantığı:
    okuyan araçlar ve otonom serbest; normal onay; plan/tanınmayan engelle.
    """
    action = evaluate_rules(rules, name, arguments)
    if action == "deny":
        return False, f"[reddedildi] kural gereği '{name}' engellendi."
    if action == "allow":
        return True, None
    if action == "ask":
        if confirm and bool(confirm(name, arguments)):
            return True, None
        return False, f"[reddedildi] '{name}' için izin verilmedi."

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
