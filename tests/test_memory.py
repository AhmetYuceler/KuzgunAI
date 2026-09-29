from kuzgun.embeddings import FakeEmbedder
from kuzgun.memory import Memory, recall_context


def test_recall_empty_returns_empty_string():
    assert recall_context(Memory(":memory:"), "soru", FakeEmbedder()) == ""


def test_recall_includes_past_exchange():
    m = Memory(":memory:")
    e = FakeEmbedder()
    m.add("python nedir", "python bir dildir", e)
    out = recall_context(m, "python hakkinda bilgi", e, k=1)
    assert "python nedir" in out
    assert "python bir dildir" in out


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


def test_works_across_threads(tmp_path):
    # Sunucu (FastAPI) yolunda add/search farklı bir thread'de koşar; çökmemeli.
    import threading

    m = Memory(str(tmp_path / "t.db"))
    e = FakeEmbedder()
    errors = []

    def worker():
        try:
            m.add("soru", "cevap", e)
            m.search("soru", e, k=1)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert errors == [], f"thread hatası: {errors}"
    assert m.count() == 1
