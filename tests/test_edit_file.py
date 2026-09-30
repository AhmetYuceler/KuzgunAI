"""edit_file: hedefli düzenleme aracı (Claude'un Edit'i gibi) — tüm dosyayı yeniden
yazmadan eski metni yenisiyle değiştirir; tekil eşleşme zorunlu (yoksa hata), diff döner.
"""

from __future__ import annotations

from kuzgun.tools.edit_file import edit_file


def test_edit_replaces_single_occurrence(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("def topla(a, b):\n    return a + b\n", encoding="utf-8")
    out = edit_file(str(f), "return a + b", "return a - b")
    assert out.startswith("Düzenlendi")
    assert f.read_text(encoding="utf-8") == "def topla(a, b):\n    return a - b\n"
    assert "-    return a + b" in out and "+    return a - b" in out  # diff


def test_edit_missing_old_string_errors(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("merhaba", encoding="utf-8")
    out = edit_file(str(f), "yok böyle metin", "x")
    assert out.startswith("Error:") and "bulunamadı" in out
    assert f.read_text(encoding="utf-8") == "merhaba"  # dokunulmadı


def test_edit_ambiguous_without_replace_all_errors(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1\nx = 1\n", encoding="utf-8")
    out = edit_file(str(f), "x = 1", "x = 2")
    assert out.startswith("Error:") and "eşleşiyor" in out
    assert f.read_text(encoding="utf-8") == "x = 1\nx = 1\n"  # değişmedi


def test_edit_replace_all(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1\nx = 1\n", encoding="utf-8")
    out = edit_file(str(f), "x = 1", "x = 2", replace_all=True)
    assert out.startswith("Düzenlendi") and "(2 değişiklik)" in out
    assert f.read_text(encoding="utf-8") == "x = 2\nx = 2\n"


def test_edit_missing_file_errors(tmp_path):
    out = edit_file(str(tmp_path / "yok.py"), "a", "b")
    assert out.startswith("Error:") and "bulunamadı" in out


def test_edit_noop_same_strings_errors(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("abc", encoding="utf-8")
    out = edit_file(str(f), "abc", "abc")
    assert out.startswith("Error:")


def test_edit_file_registered_and_mutating():
    from kuzgun.engine import build_default_registry

    reg = build_default_registry()
    assert reg.has("edit_file")
    assert reg.is_mutating("edit_file") is True  # değişiklik yapar → izin kapısına tabi
