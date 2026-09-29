"""Oturumlar-arası mesaj kutusu (Faz C11).

Claude'un cross-session mesajlaşmasının kuralı: gelen mesaj YETKİ TAŞIMAZ (onay
veremez, ayar değiştiremez — sadece veri); döngü koruması: gönderici başına hız
sınırı, kopya düşürme, kuyruk sınırı.
"""

from __future__ import annotations

from kuzgun.inbox import Inbox


def test_send_and_poll():
    box = Inbox()
    assert box.send("b", "a", "merhaba") is True
    msgs = box.poll("b")
    assert len(msgs) == 1
    assert msgs[0]["from"] == "a" and msgs[0]["text"] == "merhaba"


def test_poll_drains():
    box = Inbox()
    box.send("b", "a", "x")
    box.poll("b")
    assert box.poll("b") == []  # ikinci poll boş (drenaj)


def test_duplicate_dropped():
    box = Inbox()
    assert box.send("b", "a", "ayni") is True
    assert box.send("b", "a", "ayni") is False  # kopya düşürüldü
    assert len(box.poll("b")) == 1


def test_rate_limit_per_sender():
    box = Inbox(rate_limit=3, window=60, clock=lambda: 1000.0)
    accepted = [box.send("b", "spam", f"m{i}") for i in range(5)]
    assert accepted.count(True) == 3  # sadece 3 kabul (hız sınırı)


def test_queue_cap_drops_oldest():
    box = Inbox(max_queue=2)
    for i in range(4):
        box.send("b", f"s{i}", f"m{i}")  # farklı gönderici → kopya değil
    msgs = box.poll("b")
    assert len(msgs) == 2
    assert msgs[-1]["text"] == "m3"  # en yeni tutuldu


def test_messages_carry_no_authority():
    # Mesaj yalnız veridir: from/text/ts; onay/komut/ayar alanı YOK.
    box = Inbox()
    box.send("b", "a", "rm -rf /")
    m = box.poll("b")[0]
    assert set(m.keys()) == {"from", "text", "ts"}
