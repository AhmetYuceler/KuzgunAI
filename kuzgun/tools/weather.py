from __future__ import annotations

from urllib.parse import quote

WEATHER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "weather",
        "description": (
            "Hava durumunu verir. Şehir belirtilmezse kullanıcının konumundan (IP) "
            "otomatik bulur. 'hava durumu', 'hava nasıl', 'kaç derece' gibi sorularda "
            "bu aracı kullan (karmaşık API'ye gerek yok)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Şehir adı. Boş bırakılırsa otomatik konum.",
                }
            },
        },
    },
}


def _http_get_text(url: str) -> str:
    import urllib.request

    # wttr.in tarayıcıya HTML, curl'e düz metin verir → curl UA kullan.
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read(20000).decode("utf-8", errors="replace")


def weather(city: str = "", _fetch=None) -> str:
    loc = quote(city.strip()) if city and city.strip() else ""
    url = (
        f"https://wttr.in/{loc}"
        "?format=%l:+%C+%t,+hissedilen+%f,+nem+%h,+ruzgar+%w&lang=tr&m"
    )
    fetch = _fetch or _http_get_text
    try:
        text = fetch(url)
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"
    return text.strip()
