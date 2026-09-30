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


def test_remote_chat_sends_session():
    seen = {}

    def fake_post(url, payload):
        seen.update(payload)
        return {"reply": "ok"}

    remote_chat("x", base_url="http://x", session="benim", _post=fake_post)
    assert seen["session"] == "benim"


def test_request_carries_bearer_token():
    from kuzgun.client import _build_request

    req = _build_request("http://x/chat", {"message": "m"}, token="gizli")
    assert req.get_header("Authorization") == "Bearer gizli"


def test_request_without_token_has_no_auth_header():
    from kuzgun.client import _build_request

    req = _build_request("http://x/chat", {"message": "m"})
    assert req.get_header("Authorization") is None


def test_inbox_send_uses_post():
    from kuzgun.client import inbox_send

    seen = {}
    def fake(url, payload):
        seen["url"] = url; seen["p"] = payload
        return {"accepted": True}
    assert inbox_send("http://x", "b", "a", "selam", _post=fake) is True
    assert seen["url"].endswith("/inbox/send")
    assert seen["p"] == {"to": "b", "from": "a", "text": "selam"}


def test_inbox_poll_returns_messages():
    from kuzgun.client import inbox_poll

    out = inbox_poll("http://x", "b", _post=lambda u, p: {"messages": [{"from": "a", "text": "x"}]})
    assert out == [{"from": "a", "text": "x"}]
