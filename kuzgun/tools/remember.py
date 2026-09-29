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


def remember(fact: str, _path=None) -> str:
    if _path is None:
        from kuzgun.config import load_config

        _path = load_config().notes_path
    return add_note(_path, fact)
