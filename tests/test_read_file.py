from kuzgun.tools.read_file import read_file, READ_FILE_SCHEMA


def test_reads_existing_file(tmp_path):
    f = tmp_path / "not.txt"
    f.write_text("selam dunya", encoding="utf-8")
    assert read_file(str(f)) == "selam dunya"


def test_missing_file_returns_error(tmp_path):
    assert read_file(str(tmp_path / "yok.txt")).startswith("Error:")


def test_large_file_is_truncated_with_marker(tmp_path):
    f = tmp_path / "buyuk.txt"
    f.write_text("A" * 5000, encoding="utf-8")
    out = read_file(str(f), max_bytes=1000)
    assert len(out) < 5000
    assert out.startswith("A" * 1000)
    assert "kırpıldı" in out  # kullanıcıya/modele kırpma bildirilir


def test_does_not_load_whole_huge_file(tmp_path):
    # Akışlı okuma: max_bytes+işaret kadarını okur, tüm dosyayı belleğe almaz.
    f = tmp_path / "cok_buyuk.txt"
    f.write_text("x" * 2_000_000, encoding="utf-8")
    out = read_file(str(f), max_bytes=500)
    assert len(out) < 1000  # sadece küçük bir önizleme döndü


def test_schema_name():
    assert READ_FILE_SCHEMA["function"]["name"] == "read_file"
