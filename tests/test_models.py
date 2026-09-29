from kuzgun.models import AssistantMessage, ToolCall, FakeModelClient


def test_fake_client_returns_scripted_messages_in_order():
    scripted = [
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "read_file", {"path": "x"})]),
        AssistantMessage(text="bitti", tool_calls=[]),
    ]
    client = FakeModelClient(scripted)
    first = client.chat(messages=[], tools=[])
    assert first.tool_calls[0].name == "read_file"
    second = client.chat(messages=[], tools=[])
    assert second.text == "bitti"
