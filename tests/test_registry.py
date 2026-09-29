from kuzgun.tools import ToolRegistry

SCHEMA = {
    "type": "function",
    "function": {
        "name": "echo",
        "description": "Verilen metni geri döndürür.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
}


def test_register_and_execute():
    reg = ToolRegistry()
    reg.register(SCHEMA, lambda text: f"echo: {text}")
    assert reg.execute("echo", {"text": "selam"}) == "echo: selam"
    assert reg.schemas()[0]["function"]["name"] == "echo"


def test_unknown_tool_returns_error():
    reg = ToolRegistry()
    assert reg.execute("yok", {}).startswith("Error: unknown tool")


def test_bad_arguments_returns_error():
    reg = ToolRegistry()
    reg.register(SCHEMA, lambda text: text)
    # 'text' eksik -> TypeError yakalanmalı
    assert reg.execute("echo", {}).startswith("Error:")


def test_mutating_flag_defaults_false_and_can_be_set():
    reg = ToolRegistry()
    reg.register(SCHEMA, lambda text: text)  # varsayılan: okuyan
    reg.register(
        {
            "type": "function",
            "function": {
                "name": "yaz",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        lambda: "ok",
        mutating=True,
    )
    assert reg.is_mutating("echo") is False
    assert reg.is_mutating("yaz") is True


def test_is_mutating_unknown_is_false():
    assert ToolRegistry().is_mutating("yok") is False
