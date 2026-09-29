from kuzgun.tools.glob_search import glob_search, GLOB_SCHEMA


def test_finds_matching_files(tmp_path):
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "b.py").write_text("y", encoding="utf-8")
    (tmp_path / "c.txt").write_text("z", encoding="utf-8")
    out = glob_search("*.py", root=str(tmp_path))
    assert "a.py" in out and "b.py" in out
    assert "c.txt" not in out


def test_no_match_returns_message(tmp_path):
    out = glob_search("*.rs", root=str(tmp_path))
    assert "eşleşme" in out.lower() or "yok" in out.lower()


def test_schema_name():
    assert GLOB_SCHEMA["function"]["name"] == "glob_search"
