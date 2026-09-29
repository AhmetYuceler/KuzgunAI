from __future__ import annotations

# Windows sanal tuş kodları (medya tuşları). Spotify vb. bu tuşlara yanıt verir.
_ACTIONS = {
    "next": 0xB0, "sonraki": 0xB0, "ileri": 0xB0, "gec": 0xB0, "degistir": 0xB0,
    "previous": 0xB1, "prev": 0xB1, "onceki": 0xB1, "geri": 0xB1,
    "playpause": 0xB3, "play": 0xB3, "pause": 0xB3, "oynat": 0xB3,
    "duraklat": 0xB3, "durdur": 0xB3, "devam": 0xB3,
    "stop": 0xB2,
    "volup": 0xAF, "sesac": 0xAF, "sesyukselt": 0xAF,
    "voldown": 0xAE, "seskis": 0xAE, "sesalcalt": 0xAE,
    "mute": 0xAD, "sessiz": 0xAD,
}

MEDIA_SCHEMA = {
    "type": "function",
    "function": {
        "name": "media_control",
        "description": (
            "Bilgisayardaki müzik/medya oynatmayı kontrol eder (Spotify dahil, "
            "Windows medya tuşlarıyla). Kullanıcı 'müziği değiştir', 'sonraki şarkı', "
            "'şarkıyı geç' derse action='next'; 'önceki' → 'previous'; 'durdur/oynat/"
            "duraklat' → 'playpause'; 'sesi aç/kıs' → 'volup'/'voldown'; 'sessiz' → "
            "'mute'. Karmaşık API'ye gerek yok, bu aracı kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "next, previous, playpause, stop, volup, voldown, mute",
                }
            },
            "required": ["action"],
        },
    },
}


def _send_media_key(vk: int) -> None:
    import ctypes

    KEYEVENTF_KEYUP = 0x0002
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def media_control(action: str, _sender=None) -> str:
    key = (action or "").lower().strip().replace(" ", "").replace("_", "")
    vk = _ACTIONS.get(key)
    if vk is None:
        return (
            f"Error: bilinmeyen medya eylemi: {action}. "
            "Seçenekler: next, previous, playpause, stop, volup, voldown, mute"
        )
    sender = _sender or _send_media_key
    try:
        sender(vk)
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"
    return f"Medya komutu gönderildi: {action}"
