"""Ortak REPL çekirdeği (Faz B8): yerel CLI ve HTTP istemci aynı komut tablosu."""

from __future__ import annotations

import kuzgun.client as client_mod
from kuzgun.client import run_remote_repl
from kuzgun.repl import COMMANDS, handle_slash


def test_cli_and_client_share_same_command_table():
    # cli.py komut tablosunu repl.py'den re-export eder (tek kaynak).
    from kuzgun.cli import COMMANDS as cli_commands

    assert cli_commands is COMMANDS


def test_handle_slash_mode_switch():
    state = {"mode": "normal", "quit": False}
    assert "plan" in handle_slash("/mod plan", state)
    assert state["mode"] == "plan"
    assert handle_slash("/cikis", state) == "Görüşürüz!"
    assert state["quit"] is True


def test_remote_repl_uses_shared_commands_and_transport(monkeypatch):
    # HTTP istemci: /mod ORTAK handle_slash ile mod değiştirir; mesaj remote_chat'e gider.
    sent = []
    monkeypatch.setattr(
        client_mod, "remote_chat",
        lambda msg, base_url, mode, token, session: sent.append((msg, mode)) or f"UZAK:{msg}",
    )
    inputs = iter(["/mod plan", "merhaba", "/cikis"])
    out_lines = []

    def fake_input(prompt=""):
        return next(inputs)

    run_remote_repl("http://x:8000", cfg=_FakeCfg(), input_fn=fake_input, out=out_lines.append)
    joined = "\n".join(out_lines)
    assert "Mod değişti: plan" in joined
    assert "UZAK:merhaba" in joined
    assert sent == [("merhaba", "plan")]  # mesaj plan modunda uzağa gitti


class _FakeCfg:
    token = ""
