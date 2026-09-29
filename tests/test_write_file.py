from pathlib import Path

from kuzgun.tools.write_file import write_file, WRITE_FILE_SCHEMA


def test_writes_file(tmp_path):
    f = tmp_path / "cikti.txt"
    out = write_file(str(f), "selam")
    assert Path(f).read_text(encoding="utf-8") == "selam"
    assert out.startswith("Yaz")  # onay mesajı döndürür


def test_creates_parent_dirs(tmp_path):
    f = tmp_path / "yeni" / "alt" / "not.txt"
    write_file(str(f), "veri")
    assert Path(f).read_text(encoding="utf-8") == "veri"


def test_schema_name():
    assert WRITE_FILE_SCHEMA["function"]["name"] == "write_file"
