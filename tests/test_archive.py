"""Oturum arşivi (/resume): konuşmalar diske yazılır, listelenir, geri yüklenir."""

import os
import time

from kuzgun.archive import SessionArchive, title_for

MSGS = [
    {"role": "system", "content": "sistem"},
    {"role": "user", "content": "python ile toplama fonksiyonu yaz"},
    {"role": "assistant", "content": "def topla(a, b): return a + b"},
]


def test_save_and_load_roundtrip(tmp_path):
    a = SessionArchive(str(tmp_path))
    sid = a.new_id()
    a.save(sid, MSGS, mode="normal", cwd="C:/proje")
    messages, meta = a.load(sid)
    assert messages == MSGS
    assert meta["id"] == sid and meta["mode"] == "normal" and meta["cwd"] == "C:/proje"
    assert meta["title"] == "python ile toplama fonksiyonu yaz"
    assert meta["turns"] == 1  # kullanıcı mesajı sayısı


def test_list_is_newest_first_and_skips_empty(tmp_path):
    a = SessionArchive(str(tmp_path))
    s1, s2 = a.new_id(), a.new_id()
    a.save(s1, MSGS)
    time.sleep(0.01)
    a.save(s2, MSGS + [{"role": "user", "content": "ikinci"}])
    a.save(a.new_id(), [{"role": "system", "content": "boş"}])  # hiç kullanıcı mesajı yok
    ids = [m["id"] for m in a.list()]
    assert ids == [s2, s1]


def test_latest_and_rename(tmp_path):
    a = SessionArchive(str(tmp_path))
    sid = a.new_id()
    a.save(sid, MSGS)
    assert a.latest()["id"] == sid
    a.rename(sid, "toplama-isi")
    assert a.load(sid)[1]["name"] == "toplama-isi"
    assert a.find("toplama-isi")["id"] == sid  # ada göre bulunur
    assert a.find(sid)["id"] == sid  # id'ye göre de
    assert a.find("yok") is None


def test_sweep_removes_old_sessions(tmp_path):
    a = SessionArchive(str(tmp_path))
    old, new = a.new_id(), a.new_id()
    a.save(old, MSGS)
    a.save(new, MSGS)
    p = a.path(old)
    t = time.time() - 40 * 86400
    os.utime(p, (t, t))
    a.sweep(days=30)
    assert a.find(old) is None and a.find(new) is not None


def test_title_for_uses_first_user_message_trimmed():
    long = "a" * 100
    assert title_for([{"role": "system", "content": "s"}, {"role": "user", "content": long}]) == "a" * 57 + "..."
    assert title_for([{"role": "user", "content": "soru\n[ekli resim: x.png]"}]) == "soru"
    assert title_for([]) == "(boş)"


def test_list_filters_by_cwd_and_all(tmp_path):
    a = SessionArchive(str(tmp_path))
    s1, s2 = a.new_id(), a.new_id()
    a.save(s1, MSGS, cwd="C:/proje-a")
    time.sleep(0.01)
    a.save(s2, MSGS, cwd="C:/proje-b")
    assert [m["id"] for m in a.list(cwd="C:/proje-a")] == [s1]
    assert [m["id"] for m in a.list(cwd="c:\proje-a\\")] == [s1]  # büyük/küçük harf, eğik çizgi farkı önemsiz
    assert [m["id"] for m in a.list()] == [s2, s1]  # cwd verilmezse hepsi
    assert a.latest(cwd="C:/proje-a")["id"] == s1
    assert a.latest(cwd="C:/yok") is None
