from kuzgun.models import (
    AssistantMessage,
    ToolCall,
    FakeModelClient,
    _parse_arguments,
)


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


def test_parse_arguments_valid_json():
    assert _parse_arguments('{"path": "x"}') == {"path": "x"}


def test_parse_arguments_null_or_empty_returns_empty_dict():
    assert _parse_arguments(None) == {}
    assert _parse_arguments("") == {}


def test_parse_arguments_malformed_returns_empty_dict():
    # 7B model bozuk JSON uretirse tur cokmemeli
    assert _parse_arguments("{bozuk json") == {}


def test_parse_arguments_non_object_returns_empty_dict():
    assert _parse_arguments("[1, 2, 3]") == {}


def test_clients_satisfy_modelclient_protocol():
    from kuzgun.models import ModelClient

    assert isinstance(FakeModelClient([]), ModelClient)
