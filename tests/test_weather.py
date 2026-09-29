from kuzgun.tools.weather import weather, WEATHER_SCHEMA


def test_weather_returns_text():
    out = weather("Istanbul", _fetch=lambda url: "Istanbul: Güneşli +20°C")
    assert "Istanbul" in out and "20" in out


def test_weather_url_contains_city():
    seen = {}

    def fake(url):
        seen["url"] = url
        return "ok"

    weather("Ankara", _fetch=fake)
    assert "Ankara" in seen["url"]
    assert "wttr.in" in seen["url"]


def test_weather_error_caught():
    def boom(url):
        raise RuntimeError("ag yok")

    assert weather("X", _fetch=boom).startswith("Error:")


def test_schema_name():
    assert WEATHER_SCHEMA["function"]["name"] == "weather"
