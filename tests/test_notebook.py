from kuzgun.notebook import add_note, load_notes


def test_add_and_load(tmp_path):
    p = str(tmp_path / "notes.md")
    add_note(p, "kullanıcının adı Ahmet")
    add_note(p, "mavi rengi sever")
    notes = load_notes(p)
    assert "Ahmet" in notes and "mavi" in notes


def test_load_missing_returns_empty(tmp_path):
    assert load_notes(str(tmp_path / "yok.md")) == ""


def test_add_empty_is_error(tmp_path):
    assert add_note(str(tmp_path / "n.md"), "   ").startswith("Error:")
