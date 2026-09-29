from kuzgun.embeddings import FakeEmbedder
from kuzgun.memory import Memory


def test_empty_search_returns_empty():
    m = Memory(":memory:")
    assert m.search("herhangi bir sey", FakeEmbedder(), k=3) == []


def test_add_and_search_returns_relevant_first():
    m = Memory(":memory:")
    e = FakeEmbedder()
    m.add("python programlama", "python bir dildir", e)
    m.add("kedi hayvan", "kedi bir memelidir", e)
    hits = m.search("python nedir", e, k=1)
    assert len(hits) == 1
    assert "python" in hits[0]["user"]


def test_count_increments():
    m = Memory(":memory:")
    e = FakeEmbedder()
    assert m.count() == 0
    m.add("a", "b", e)
    m.add("c", "d", e)
    assert m.count() == 2


def test_persists_to_file(tmp_path):
    db = str(tmp_path / "mem.db")
    e = FakeEmbedder()
    Memory(db).add("merhaba", "selam", e)
    assert Memory(db).count() == 1  # aynı dosyayı yeniden aç
