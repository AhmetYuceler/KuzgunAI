from kuzgun.tools.web_search import web_search, WEB_SEARCH_SCHEMA


def _fake(results):
    return lambda query, max_results: results


def test_formats_results():
    out = web_search(
        "python",
        _search=_fake(
            [{"title": "Python", "href": "https://python.org", "body": "resmi site"}]
        ),
    )
    assert "Python" in out and "https://python.org" in out and "resmi site" in out


def test_no_results_message():
    out = web_search("xyzzy", _search=_fake([]))
    assert "sonuç yok" in out.lower()


def test_search_error_is_caught():
    def boom(query, max_results):
        raise RuntimeError("ag hatasi")

    out = web_search("x", _search=boom)
    assert out.startswith("Error:")


def test_schema_name():
    assert WEB_SEARCH_SCHEMA["function"]["name"] == "web_search"
