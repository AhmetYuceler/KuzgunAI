from kuzgun.tools.media_control import media_control, MEDIA_SCHEMA


def test_next_sends_next_key():
    sent = []
    media_control("next", _sender=sent.append)
    assert sent == [0xB0]


def test_turkish_alias_sonraki():
    sent = []
    media_control("sonraki", _sender=sent.append)
    assert sent == [0xB0]


def test_playpause_key():
    sent = []
    media_control("duraklat", _sender=sent.append)
    assert sent == [0xB3]


def test_unknown_action_error():
    assert media_control("uçmak", _sender=lambda vk: None).startswith("Error:")


def test_schema_name():
    assert MEDIA_SCHEMA["function"]["name"] == "media_control"
