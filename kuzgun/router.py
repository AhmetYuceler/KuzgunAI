from __future__ import annotations

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
