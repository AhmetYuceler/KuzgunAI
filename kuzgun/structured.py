"""Yapılandırılmış (JSON) model çıktısı (Faz C1).

Küçük modeller serbest metne kayar; alt-ajan/planlama gibi yerlerde ÇIKTIYI JSON'a
zorlar, geçersizse düzeltme isteğiyle birkaç kez yeniden dener. Böylece orkestratör
planı gibi yapılar serbest-metin ayrıştırmaya bağlı kalmaz.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from kuzgun.logging_setup import get_logger

log = get_logger("structured")

_JSON_INSTRUCTION = (
    "Yalnızca GEÇERLİ JSON döndür (nesne ya da dizi). Açıklama, markdown, kod bloğu "
    "işareti EKLEME; sadece ham JSON yaz."
)


def _extract_json(text: str | None):
    """Metindeki ilk dengeli JSON değerini ({...} ya da [...]) ayrıştırıp döndürür.
    Önce tüm metni dener; olmazsa ilk açılış işaretinden dengeli bir bölge tarar."""
    if not text:
        return None
    text = text.strip()
    # Kod bloğu işaretlerini temizle.
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        return None
    start = min(starts)
    open_ch = text[start]
    close_ch = "}" if open_ch == "{" else "]"
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            esc = (c == "\\") and not esc
            if c == '"' and not esc:
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except Exception:
                    return None
    return None


def complete_json(
    client,
    messages: list[dict],
    retries: int = 3,
    default=None,
    validate: Callable[[object], bool] | None = None,
):
    """Modelden JSON çıktı ister; geçersiz/şema-dışıysa düzeltme mesajıyla yeniden
    dener. `retries` kez daha denenir (toplam retries+1). Başarısızsa `default` döner.

    `validate(obj) -> bool`: ayrıştırılan JSON'u kabul/ret eder (ör. gerekli anahtar)."""
    convo = [*messages, {"role": "system", "content": _JSON_INSTRUCTION}]
    for attempt in range(retries + 1):
        assistant = client.chat(convo, [])
        parsed = _extract_json(assistant.text)
        if parsed is not None and (validate is None or validate(parsed)):
            return parsed
        log.info("structured: geçersiz JSON (deneme %d/%d)", attempt + 1, retries + 1)
        convo = [
            *convo,
            {"role": "assistant", "content": assistant.text or ""},
            {"role": "user", "content": "Çıktın geçerli/uygun JSON değildi. " + _JSON_INSTRUCTION},
        ]
    return default
