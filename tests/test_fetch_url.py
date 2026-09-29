from kuzgun.tools.fetch_url import fetch_url, FETCH_URL_SCHEMA, UNTRUSTED_PREFIX


def test_rejects_non_http_scheme():
    out = fetch_url("file:///etc/passwd", _fetch=lambda u: "gizli")
    assert out.startswith("Error:")


def test_extracts_text_and_marks_untrusted():
    html = (
        "<html><head><style>x{}</style></head><body><p>Merhaba dünya</p>"
        "<script>alert(1)</script></body></html>"
    )
    out = fetch_url("https://ornek.com", _fetch=lambda u: html)
    assert out.startswith(UNTRUSTED_PREFIX)
    assert "Merhaba dünya" in out
    assert "alert(1)" not in out  # script atılmalı


def test_fetch_error_is_caught():
    def boom(url):
        raise RuntimeError("baglanti yok")

    out = fetch_url("https://ornek.com", _fetch=boom)
    assert out.startswith("Error:")


def test_schema_name():
    assert FETCH_URL_SCHEMA["function"]["name"] == "fetch_url"
