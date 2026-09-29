from kuzgun.notebook import load_notes
from kuzgun.tools.remember import remember, REMEMBER_SCHEMA


def test_remember_writes_to_notes(tmp_path):
    p = str(tmp_path / "n.md")
    remember("kullanıcı Python seviyor", _path=p)
    assert "Python" in load_notes(p)


def test_schema_name():
    assert REMEMBER_SCHEMA["function"]["name"] == "remember"
