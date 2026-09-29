from kuzgun.permissions import is_allowed


def test_read_tool_allowed_in_every_mode():
    for mode in ("plan", "normal", "otonom"):
        ok, msg = is_allowed("read_file", {}, mutating=False, mode=mode)
        assert ok is True and msg is None


def test_plan_mode_blocks_mutating():
    ok, msg = is_allowed("write_file", {}, mutating=True, mode="plan")
    assert ok is False and "plan" in msg.lower()


def test_normal_mode_mutating_denied_without_confirm():
    ok, msg = is_allowed("write_file", {}, mutating=True, mode="normal", confirm=None)
    assert ok is False


def test_normal_mode_mutating_allowed_when_confirmed():
    ok, msg = is_allowed(
        "write_file", {}, mutating=True, mode="normal", confirm=lambda name, args: True
    )
    assert ok is True and msg is None


def test_normal_mode_mutating_denied_when_rejected():
    ok, msg = is_allowed(
        "write_file", {}, mutating=True, mode="normal", confirm=lambda name, args: False
    )
    assert ok is False


def test_autonomous_mode_allows_mutating():
    ok, msg = is_allowed("run_command", {}, mutating=True, mode="otonom")
    assert ok is True
