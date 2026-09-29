"""Engine geçmiş doğruluğu testleri (Faz A3).

Ayrı dosyada tutuluyor (test_engine.py başka bir oturumca da düzenleniyor;
merge çakışması olmasın).
"""

from __future__ import annotations

import pytest

from kuzgun.models import AssistantMessage


def test_extra_context_injected_into_every_session(make_engine):
    # B4 kancası: proje-özel bağlam (ör. çalışma klasörünün KUZGUN.md'si) her
    # oturumun sistem bağlamına girer — peer'ın "proje analizi" işi engine'e
    # dokunmadan bunu kullanabilsin.
    eng = make_engine(extra_context="[Proje notu] Bu bir FastAPI projesidir.")
    assert any("FastAPI projesidir" in m.get("content", "") for m in eng.messages)
    assert any(
        "FastAPI projesidir" in m.get("content", "") for m in eng.history("yeni-oturum")
    )


class _BoomClient:
    """chat çağrılınca patlar (ağ hatası benzeri)."""

    def chat(self, messages, tools):
        raise RuntimeError("model erişilemez")


def test_history_not_corrupted_when_model_raises(make_engine):
    # A3 (bug #6): model turu hata verirse, eklenen kullanıcı mesajı geçmişte
    # SARKAN kalmamalı; geçmiş tur öncesi haline dönmeli.
    eng = make_engine()
    eng.client = _BoomClient()  # model çağrısı patlar (devretme değil, ham hata)
    before = len(eng.messages)
    with pytest.raises(RuntimeError):
        eng.chat("bir sey sor")
    assert len(eng.messages) == before                      # geçmiş temiz
    assert all(m.get("role") != "user" or m["content"] != "bir sey sor"
               for m in eng.messages)                       # sarkan kullanıcı yok


def test_history_not_corrupted_on_second_call(make_engine):
    # Hatalı turdan sonra normal tur düzgün işlemeli (geçmiş bozulmadı).
    eng = make_engine()
    eng.client = _BoomClient()
    with pytest.raises(RuntimeError):
        eng.chat("patlat")
    from kuzgun.models import FakeModelClient
    eng.client = FakeModelClient([AssistantMessage(text="ikinci ok", tool_calls=[])])
    assert eng.chat("normal soru") == "ikinci ok"
