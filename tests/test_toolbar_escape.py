"""Regresyon: durum barındaki dinamik metin (araç aktivitesi) '<', '>', '&'
içerince prompt_toolkit HTML ayrıştırması kırılıp TÜM uygulama çöküyordu
(minidom 'not well-formed'). Toolbar bu karakterleri kaçırmalı, çökmemeli.
"""

from __future__ import annotations

from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.output import DummyOutput

from kuzgun import ui


def _toolbar_for(busy: str):
    state = {"mode": "otonom", "busy": busy, "queue": [], "attachments": []}
    with create_pipe_input() as inp:
        session = ui.make_session(state, input=inp, output=DummyOutput())
        return session.bottom_toolbar()  # çağırınca HTML kurar — kırık metinde patlardı


def test_busy_with_angle_brackets_does_not_crash():
    # Gerçek vaka: araç aktivitesi komut/desen icerir ('<tool_call>', 'grep <x>').
    ft = _toolbar_for("⚙️ komut çalıştırıyor · grep '<pattern>' & echo a > b")
    assert ft is not None  # istisna atmadan HTML üretildi


def test_busy_with_ampersand_does_not_crash():
    ft = _toolbar_for("📄 dosya okuyor · a&b<c>d.py")
    assert ft is not None


def test_esc_replaces_specials():
    assert ui._esc("a<b>&c") == "a&lt;b&gt;&amp;c"
