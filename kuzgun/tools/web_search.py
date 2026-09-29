from __future__ import annotations

WEB_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "İnternette arama yapar ve ilk sonuçları (başlık, adres, özet) döndürür. "
            "Güncel bilgi ya da bir konuda kaynak bulmak için kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Arama sorgusu."},
                "max_results": {
                    "type": "integer",
                    "description": "Kaç sonuç. Varsayılan 5.",
                },
            },
            "required": ["query"],
        },
    },
}


def _ddgs_search(query: str, max_results: int) -> list[dict]:
    from ddgs import DDGS

    with DDGS() as d:
        return list(d.text(query, max_results=max_results))


def web_search(query: str, max_results: int = 5, _search=None) -> str:
    search = _search or _ddgs_search
    try:
        results = search(query, max_results)
    except Exception as exc:
        return f"Error: {exc}"
    if not results:
        return "Sonuç yok."
    lines = []
    for r in results:
        baslik = r.get("title", "")
        adres = r.get("href") or r.get("url") or ""
        ozet = r.get("body", "")
        lines.append(f"- {baslik}\n  {adres}\n  {ozet}")
    return "\n".join(lines)
