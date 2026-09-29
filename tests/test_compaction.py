"""Bağlam sıkıştırma / compaction (Faz C6).

Bütçe aşılınca eski turlar ATILMAK yerine ÖZETLENİR; son K tur olduğu gibi kalır;
baştaki sistem+notlar korunur. Olgular zaten her turda SQLite'a yazıldığı için özet
detay kaybetse de bilgi hafızada durur.
"""

from __future__ import annotations

from kuzgun.models import AssistantMessage, FakeModelClient


def _engine_with_summary(make_engine, summary_text):
    eng = make_engine()
    eng.client = FakeModelClient([AssistantMessage(text=summary_text, tool_calls=[])] * 5)
    eng.config = eng.config.__class__(**{**eng.config.__dict__, "compaction": True})
    return eng


def test_compact_summarizes_old_and_keeps_recent(make_engine):
    eng = _engine_with_summary(make_engine, "ÖZET: eski konuşma buydu")
    eng.max_history = 8
    msgs = [{"role": "system", "content": "sistem"}]
    for i in range(20):
        msgs.append({"role": "user", "content": f"soru {i}"})
        msgs.append({"role": "assistant", "content": f"cevap {i}"})
    eng._compact(msgs)
    assert len(msgs) <= eng.max_history
    assert msgs[0]["role"] == "system"
    assert any("ÖZET" in m.get("content", "") for m in msgs)   # eski turlar özetlendi
    assert any("soru 19" in m.get("content", "") for m in msgs)  # son turlar korundu


def test_compact_noop_when_within_budget(make_engine):
    eng = _engine_with_summary(make_engine, "özet")
    eng.max_history = 24
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "merhaba"}]
    before = list(msgs)
    eng._compact(msgs)
    assert msgs == before  # bütçe içinde → dokunma (model çağrılmaz)


def test_trim_uses_drop_when_compaction_disabled(make_engine):
    # compaction kapalıyken eski davranış (özetleme yok, kırpma).
    eng = make_engine()
    eng.max_history = 6
    msgs = [{"role": "system", "content": "s"}]
    for i in range(20):
        msgs.append({"role": "user", "content": f"u{i}"})
        msgs.append({"role": "assistant", "content": f"a{i}"})
    eng._trim(msgs)
    assert len(msgs) <= eng.max_history
    assert not any("ÖZET" in m.get("content", "") for m in msgs)
