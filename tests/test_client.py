from kuzgun.client import remote_chat


def test_remote_chat_posts_and_parses():
    captured = {}

    def fake_post(url, payload):
        captured["url"] = url
        captured["payload"] = payload
        return {"reply": "merhaba"}

    out = remote_chat("selam", base_url="http://x:8000", mode="normal", _post=fake_post)
    assert out == "merhaba"
    assert captured["url"].endswith("/chat")
    assert captured["payload"]["message"] == "selam"
    assert captured["payload"]["mode"] == "normal"


def test_remote_chat_strips_trailing_slash():
    seen = {}

    def fake_post(url, payload):
        seen["url"] = url
        return {"reply": "ok"}

    remote_chat("x", base_url="http://x:8000/", _post=fake_post)
    assert seen["url"] == "http://x:8000/chat"


def test_remote_chat_error_is_caught():
    def boom(url, payload):
        raise RuntimeError("baglanti yok")

    assert remote_chat("x", base_url="http://x", _post=boom).startswith("Error:")
