from kuzgun.tools.read_file import read_file, READ_FILE_SCHEMA


def test_reads_existing_file(tmp_path):
    f = tmp_path / "not.txt"
    f.write_text("selam dunya", encoding="utf-8")
    assert read_file(str(f)) == "selam dunya"


def test_missing_file_returns_error(tmp_path):
    assert read_file(str(tmp_path / "yok.txt")).startswith("Error:")


def test_schema_name():
    assert READ_FILE_SCHEMA["function"]["name"] == "read_file"
