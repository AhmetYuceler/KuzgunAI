from kuzgun.cli import build_default_registry


def test_default_registry_has_core_tools():
    names = [s["function"]["name"] for s in build_default_registry().schemas()]
    assert "read_file" in names
    assert "run_command" in names
