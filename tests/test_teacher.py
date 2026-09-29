from kuzgun.teacher import ask_claude


def test_returns_runner_answer():
    out = ask_claude("2+2 kaç?", _runner=lambda q: "4")
    assert out == "4"


def test_passes_stripped_question_to_runner():
    seen = {}

    def runner(q):
        seen["q"] = q
        return "ok"

    ask_claude("  merhaba  ", _runner=runner)
    assert seen["q"] == "merhaba"


def test_runner_error_is_caught():
    def boom(q):
        raise RuntimeError("claude yok")

    assert ask_claude("x", _runner=boom).startswith("Error:")


def test_empty_question_rejected():
    assert ask_claude("   ", _runner=lambda q: "x").startswith("Error:")
