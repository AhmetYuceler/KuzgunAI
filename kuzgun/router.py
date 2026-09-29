from __future__ import annotations

import re

# Açıkça "zor / çok-adımlı ajanik" işaret eden kalıplar. Yerel 7B model bunlarda
# güvenilmez olduğu için (bkz. Faz 7 bulgular) doğrudan uzmana (Claude) yönlendirilir.
_HARD_PATTERNS = (
    "react",
    "vite",
    "next.js",
    "nextjs",
    "angular",
    "vue",
    "npm install",
    "npm create",
    "proje oluştur",
    "proje kur",
    "uygulama kur",
    "uygulama oluştur",
    "uygulama yap",
    "site yap",
    "web sitesi",
    "scaffold",
    "refactor",
    "yeniden yapılandır",
    "mimari kur",
    "çok dosya",
)


def classify_complexity(message: str) -> tuple[str, str | None]:
    """Mesajı kabaca sınıflar: ('zor', eşleşen_kalıp) ya da ('kolay', None).

    Yalnızca AÇIKÇA zor/ajanik-kodlama işaretlerini 'zor' sayar (tutucu); geri
    kalan her şey yerel modelde işlenir.
    """
    low = message.lower()
    for pat in _HARD_PATTERNS:
        if pat in low:
            return "zor", pat
    return "kolay", None


# Kod işareti veren kalıplar (alt-dize eşleşmesi; Türkçe ekler nedeniyle \b değil).
_CODE_SUBSTR = (
    "python",
    "javascript",
    "typescript",
    "kotlin",
    "golang",
    "fonksiyon",
    "function",
    "metod",
    "algoritma",
    "regex",
    "script",
    "kod",
    "sql",
    "html",
    "css",
    "debug",
    "derle",
    "compile",
    ".py",
    ".js",
    ".ts",
)


def is_code_task(message: str) -> bool:
    """Mesaj bir kodlama işi mi? (kod-uzmanı modele yönlendirmek için)."""
    low = message.lower()
    return any(s in low for s in _CODE_SUBSTR)


# Medya/müzik niyeti → doğrudan media_control action'ı (7B'nin araç seçimine güvenmeden).
_MEDIA_INTENTS = (
    ("next", ("müziği değiştir", "muzigi degistir", "müzigi degistir", "sonraki şarkı",
              "sonraki sarki", "şarkıyı geç", "sarkiyi gec", "şarkı geç", "sonraki parça",
              "başka şarkı", "diğer şarkı", "müziği geç", "next track")),
    ("previous", ("önceki şarkı", "onceki sarki", "bir önceki", "şarkıyı geri",
                  "previous track", "geri sar")),
    ("playpause", ("müziği durdur", "muzigi durdur", "şarkıyı durdur", "müziği duraklat",
                   "müziği oynat", "müziği başlat", "müziği devam", "müzik durdur", "müzik oynat")),
    ("volup", ("sesi aç", "sesi yükselt", "ses yükselt", "sesi arttır", "sesi artır")),
    ("voldown", ("sesi kıs", "sesi azalt", "ses azalt", "sesi düşür")),
    ("mute", ("sessiz yap", "sesi kapat", "mute")),
)


def detect_media_intent(message: str) -> str | None:
    """Mesaj net bir medya komutuysa (müziği değiştir, sesi aç…) action döner; değilse None."""
    low = message.lower()
    for action, phrases in _MEDIA_INTENTS:
        if any(p in low for p in phrases):
            return action
    return None


_WEATHER_PHRASES = (
    "hava durumu", "hava nasıl", "hava nasil", "bugün hava", "bugun hava",
    "yarın hava", "kaç derece", "kac derece", "sıcaklık kaç", "yağmur var mı",
    "hava sıcak", "hava soğuk", "weather",
)


def detect_weather_intent(message: str) -> bool:
    """Mesaj bir hava durumu sorusu mu?"""
    low = message.lower()
    return any(p in low for p in _WEATHER_PHRASES)


def is_compound(message: str) -> bool:
    """Mesajda birden fazla soru/cümle var mı? ('hava kaç derece? 2x2 kaç?')

    Deterministik kısayollar (hava, medya) yalnız TEK niyetli mesajda modeli
    atlamalı; bileşik mesajda diğer sorular yutulmasın diye model de çalışır.
    """
    parts = [p for p in re.split(r"[?.!\n]+", message) if p.strip()]
    return len(parts) > 1
