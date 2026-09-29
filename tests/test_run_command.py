import time

from kuzgun.tools.run_command import run_command, RUN_COMMAND_SCHEMA


def test_runs_simple_command():
    out = run_command("echo merhaba")
    assert "merhaba" in out


def test_timeout_terminates_promptly_and_returns_error():
    # 30 pinglik (~29sn) komut, 1sn zaman asimiyla kesilmeli.
    start = time.monotonic()
    out = run_command("ping -n 30 127.0.0.1", timeout=1)
    elapsed = time.monotonic() - start
    assert "Error:" in out or "zaman" in out.lower()
    # Surec agaci gercekten oldurulduyse cok daha erken donmeli (dogal sure ~29sn).
    assert elapsed < 10, f"zaman asimi surec agacini oldurmedi; {elapsed:.1f}sn surdu"


def test_schema_name():
    assert RUN_COMMAND_SCHEMA["function"]["name"] == "run_command"
