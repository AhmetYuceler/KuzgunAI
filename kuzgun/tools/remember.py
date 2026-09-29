from __future__ import annotations

from kuzgun.notebook import add_note

REMEMBER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "remember",
        "description": (
            "Kullanıcı hakkında kalıcı bir bilgiyi/tercihi hatırlar (sonraki "
            "oturumlarda da erişilir). 'şunu hatırla', 'aklında tut', 'not al' "
            "gibi isteklerde kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "fact": {"type": "string", "description": "Hatırlanacak bilgi."}
            },
            "required": ["fact"],
        },
    },
}


def remember(fact: str, _path: str) -> str:
    """Bir bilgiyi kalıcı not dosyasına ekler.

    `_path` şemada YOK; model geçemez (ToolRegistry reddeder). Notes yolu, aracı
    kaydeden bootstrap tarafından `functools.partial` ile bağlanır (B3), ya da
    doğrudan çağıran (CLI /hatirla) tarafından verilir — böylece bu modül config'e
    bağımlı değildir."""
    return add_note(_path, fact)
