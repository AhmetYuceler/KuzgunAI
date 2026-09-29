from kuzgun.embeddings import FakeEmbedder
from kuzgun.memory import Memory, MemoryStore, recall_context


class _DimEmbedder:
    """Sabit boyutlu deterministik embedder (boyut uyumsuzluğu testleri için)."""

    def __init__(self, dim, model="dim-test"):
        self.dim = dim
        self.model = model

    def embed(self, text):
        v = [0.0] * self.dim
        for i, ch in enumerate(text):
            v[i % self.dim] += ord(ch) % 7
        return v


class _AxisEmbedder:
    """Metnin ilk harfine göre tek bir eksene 1 koyar → ilgisiz metinler ortogonal."""

    model = "axis"

    def embed(self, text):
        v = [0.0] * 5
        v[(ord(text.strip()[:1] or "a") % 5)] = 1.0
        return v


def test_memory_store_protocol():
    assert isinstance(Memory(":memory:"), MemoryStore)


def test_search_skips_dimension_mismatch():
    # B7: embedding modeli değişince (boyut farkı) eski kayıtlar sessiz çöp üretmesin.
    m = Memory(":memory:")
    m.add("eski kayit", "eski cevap", _DimEmbedder(3))
    hits = m.search("eski kayit", _DimEmbedder(8), k=5)  # farklı boyut
    assert hits == []  # uyumsuz boyut atlandı, çökme yok


def test_min_score_filters_irrelevant():
    # B7: eşik altındaki (alakasız) hatıralar geri çağrılmamalı.
    m = Memory(":memory:")
    e = _AxisEmbedder()
    m.add("apple", "meyve", e)     # 'a' ekseni
    m.add("xyz", "alakasiz", e)    # farklı eksen (ortogonal)
    hits = m.search("apple", e, k=5, min_score=0.5)
    assert len(hits) == 1
    assert hits[0]["user"] == "apple"


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
