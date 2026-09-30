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


def test_ollama_client_has_request_timeout():
    from kuzgun.models import OllamaClient

    assert OllamaClient(timeout=7).client_timeout == 7
    assert OllamaClient().client_timeout > 0  # varsayılan: sonsuz bekleme yok


def test_strip_thinking_removes_think_block():
    from kuzgun.models import _strip_thinking

    assert _strip_thinking("<think>uzun akıl yürütme</think>\n\nMerhaba") == "Merhaba"
    assert _strip_thinking("Sadece cevap") == "Sadece cevap"   # think yoksa aynen
    assert _strip_thinking("<think>a</think><think>b</think>Son") == "Son"


def test_strip_thinking_keeps_original_if_only_thinking():
    from kuzgun.models import _strip_thinking

    # Yanıt tamamen think ise (nadiren), boş dönmek yerine orijinali koru.
    out = _strip_thinking("<think>sadece düşündüm</think>")
    assert out  # boş değil
