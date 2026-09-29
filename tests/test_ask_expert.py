from kuzgun.tools.ask_expert import ask_expert, ASK_EXPERT_SCHEMA


def test_schema_name():
    assert ASK_EXPERT_SCHEMA["function"]["name"] == "ask_expert"


def test_empty_question_returns_error():
    # ask_claude'a devreder; boş soru Error döner (gerçek claude çağrılmaz)
    assert ask_expert("   ").startswith("Error:")


def test_delegates_answer():
    # _runner enjeksiyonu ask_claude üzerinden geçer
    assert ask_expert("soru", _runner=lambda q: "uzman cevabı") == "uzman cevabı"
