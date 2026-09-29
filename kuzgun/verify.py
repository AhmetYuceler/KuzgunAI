from __future__ import annotations

import re

_BLOCK_RE = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_code_blocks(text: str | None, lang: str = "python") -> list[str]:
    """Metindeki ```python ...``` (veya çıplak ```) kod bloklarını çıkarır."""
    if not text:
        return []
    return [m.group(1).strip() for m in _BLOCK_RE.finditer(text)]


def check_python_syntax(code: str) -> tuple[bool, str | None]:
    """Kodu ÇALIŞTIRMADAN sözdizimini denetler (compile). (geçerli_mi, hata)."""
    try:
        compile(code, "<kod>", "exec")
    except SyntaxError as exc:
        satir = f" (satır {exc.lineno})" if exc.lineno else ""
        return False, f"{exc.msg}{satir}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    return True, None
