from kuzgun.tools.grep_search import grep_search, GREP_SCHEMA


def test_finds_pattern_in_files(tmp_path):
    (tmp_path / "a.txt").write_text("merhaba dünya\nikinci satır", encoding="utf-8")
    (tmp_path / "b.txt").write_text("baska içerik", encoding="utf-8")
    out = grep_search("dünya", root=str(tmp_path))
    assert "a.txt" in out and "merhaba dünya" in out
    assert "b.txt" not in out


def test_invalid_regex_returns_error(tmp_path):
    out = grep_search("(bozuk", root=str(tmp_path))
    assert out.startswith("Error:")


def test_ignores_vendor_dirs(tmp_path):
    (tmp_path / "kod.py").write_text("hedef burada", encoding="utf-8")
    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "paket.py").write_text("hedef burada", encoding="utf-8")
    out = grep_search("hedef", root=str(tmp_path))
    assert "kod.py" in out
    assert ".venv" not in out


def test_schema_name():
    assert GREP_SCHEMA["function"]["name"] == "grep_search"
