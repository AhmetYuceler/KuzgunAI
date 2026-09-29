"""Parametre-eşleşmeli izin kuralları (Faz C5).

Deterministik allow/deny/ask kuralları: `allow run_command(cmd:git *)`,
`deny write_file(path:*Windows*)`. Model zekâsına DAYANMAZ (auto mode'un güvenilmez
sınıflandırıcı kısmı değil) — sadece kalıp eşleşmesi.
"""

from __future__ import annotations

from kuzgun.permissions import evaluate_rules, is_allowed, parse_rules


def test_parse_and_deny_blocks_even_in_otonom():
    rules = parse_rules("deny write_file(path:*Windows*)")
    ok, reason = is_allowed(
        "write_file", {"path": "C:/Windows/system32/x"}, True, "otonom", None, rules=rules
    )
    assert ok is False
    assert "reddedildi" in reason.lower() or "deny" in reason.lower()


def test_allow_rule_permits_in_normal_without_confirm():
    rules = parse_rules("allow run_command(cmd:git *)")
    # normal modda onaysız normalde reddedilirdi; allow kuralı geçiş sağlar.
    ok, _ = is_allowed("run_command", {"cmd": "git status"}, True, "normal", None, rules=rules)
    assert ok is True


def test_allow_rule_does_not_match_other_values():
    rules = parse_rules("allow run_command(cmd:git *)")
    ok, _ = is_allowed("run_command", {"cmd": "rm -rf /"}, True, "normal", None, rules=rules)
    assert ok is False  # kural eşleşmez → normal mod (onay yok) → reddedilir


def test_ask_rule_requires_confirm():
    rules = parse_rules("ask run_command(cmd:*)")
    ok_yes, _ = is_allowed(
        "run_command", {"cmd": "ls"}, True, "otonom", lambda n, a: True, rules=rules
    )
    ok_no, _ = is_allowed(
        "run_command", {"cmd": "ls"}, True, "otonom", lambda n, a: False, rules=rules
    )
    assert ok_yes is True and ok_no is False  # otonom'da bile ask → onaya sorar


def test_tool_only_rule_matches_any_args():
    rules = parse_rules("deny run_command")
    ok, _ = is_allowed("run_command", {"cmd": "herhangi"}, True, "otonom", None, rules=rules)
    assert ok is False


def test_no_rule_falls_back_to_mode_logic():
    rules = parse_rules("allow read_file")
    # write_file için kural yok → normal mod (onaysız) → reddedilir (eski davranış)
    ok, _ = is_allowed("write_file", {"path": "x"}, True, "normal", None, rules=rules)
    assert ok is False


def test_deny_takes_precedence_over_allow():
    rules = parse_rules("allow run_command(cmd:*)\ndeny run_command(cmd:*rm *)")
    assert evaluate_rules(rules, "run_command", {"cmd": "rm x"}) == "deny"
    assert evaluate_rules(rules, "run_command", {"cmd": "ls"}) == "allow"


def test_empty_rules_no_effect():
    assert parse_rules("") == []
    ok, _ = is_allowed("write_file", {"path": "x"}, True, "otonom", None, rules=[])
    assert ok is True  # kural yok → mod mantığı (otonom serbest)
