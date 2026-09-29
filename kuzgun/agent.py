from __future__ import annotations

import json
import re
import uuid

from kuzgun.logging_setup import get_logger, timed
from kuzgun.models import AssistantMessage, ToolCall
from kuzgun.permissions import is_allowed
from kuzgun.tools import ToolRegistry, ToolResult

log = get_logger("agent")

# B6: araç çıktısı bağlamı doldurmasın; bundan uzunsa kırpılıp geçmişe öyle girer.
MAX_TOOL_CHARS = 4000


def _clip(text: str, limit: int = MAX_TOOL_CHARS) -> str:
    """Uzun araç çıktısını baş+son koruyarak kırpar (7B'nin küçük bağlamı için)."""
    if len(text) <= limit:
        return text
    head = text[: limit // 2]
    tail = text[-limit // 4 :]
    atlanan = len(text) - len(head) - len(tail)
    return f"{head}\n... [{atlanan} karakter kırpıldı] ...\n{tail}"


def _first_json_object(text: str) -> str | None:
    """Metindeki ilk DENGELİ {...} nesnesini döndürür (fazla kapanış parantezi tolere)."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def extract_tool_calls_from_text(text: str | None) -> list[ToolCall]:
    """Model, araç çağrısını gerçek çağrı yerine metin-JSON olarak verirse yakalar.

    Örn: '```json {"name":"write_file","arguments":{...}}```' → ToolCall.
    Küçük modellerin sık yaptığı format hatasını telafi eder.
    """
    if not text:
        return []
    blob = _first_json_object(text)
    if not blob:
        return _pseudo_call(text)
    try:
        data = json.loads(blob)
    except Exception:
        return _pseudo_call(text)
    if not isinstance(data, dict):
        return []
    name = data.get("name") or data.get("tool")
    args = data.get("arguments")
    if args is None:
        args = data.get("parameters", {})
    if name and isinstance(args, dict):
        return [ToolCall(id="text-1", name=str(name), arguments=args)]
    return []


_PSEUDO_CALL = re.compile(r"(?m)^\s*([a-z_][a-z0-9_]*)\((.*)\)\s*$")
_KWARG = re.compile(r"""\s*([a-z_][a-z0-9_]*)\s*=\s*("([^"\\]|\\.)*"|'([^'\\]|\\.)*'|-?\d+(\.\d+)?|true|false|True|False)\s*(,|$)""")


def _pseudo_call(text: str) -> list[ToolCall]:
    """Metinde Python-çağrısı gibi yazılmış araç: `web_search(query="...")`.

    7B model bazen aracı çağırmak yerine bunu satır olarak yazıp bırakıyor
    (görsel akışında gözlendi). Yalnız kendi satırında, tamamı anahtar=değer
    (dize/sayı/bool) argümanlı çağrıyı kabul eder; kod bloğu içindeki çağrılar
    metin sayılır (``` içinde değilse). Kayıtlı araç mı kontrolü çağıran yapar.
    """
    if "```" in text:
        return []
    m = _PSEUDO_CALL.search(text)
    if not m:
        return []
    name, raw = m.group(1), m.group(2).strip()
    args: dict = {}
    pos = 0
    while pos < len(raw):
        km = _KWARG.match(raw, pos)
        if not km:
            return []
        key, val = km.group(1), km.group(2)
        if val[0] in "\"'":
            val = val[1:-1].replace("\\" + val[0], val[0])
        elif val in ("true", "True"):
            val = True
        elif val in ("false", "False"):
            val = False
        else:
            val = float(val) if "." in val else int(val)
        args[key] = val
        pos = km.end()
    return [ToolCall(id="text-1", name=name, arguments=args)]


def _assistant_to_history(msg: AssistantMessage) -> dict:
    entry: dict = {"role": "assistant", "content": msg.text or ""}
    if msg.tool_calls:
        entry["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
            }
            for tc in msg.tool_calls
        ]
    return entry


def _last_user_text(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def run_turn(
    client,
    messages: list[dict],
    registry: ToolRegistry,
    mode: str = "normal",
    confirm=None,
    max_steps: int = 10,
    escalate=None,
) -> str:
    """Ajan döngüsü. `escalate` verilirse, model döngüye girer / araçlar üst üste
    hata verir / max_steps aşılırsa otomatik olarak uzmana (Claude) devreder."""
    def _escalate_and_record() -> str:
        # A3 (bug #5): devredilen cevabı geçmişe de yaz ki sonraki turda kaybolmasın.
        reply = escalate(_last_user_text(messages))
        messages.append({"role": "assistant", "content": reply})
        return reply

    turn_id = uuid.uuid4().hex[:8]
    log.info("tur başladı id=%s mode=%s", turn_id, mode)
    last_sig = None
    repeat = 0
    err_streak = 0
    for step in range(max_steps):
        with timed(log, "model", id=turn_id, step=step):
            assistant = client.chat(messages, registry.schemas())
        # Model tool call'u metin-JSON olarak verdiyse gerçek çağrıya çevir.
        if not assistant.tool_calls:
            recovered = extract_tool_calls_from_text(assistant.text)
            # Yalnız KAYITLI bir aracı gösteriyorsa çağrı say; değilse cevap JSON'dur.
            if recovered and all(registry.has(tc.name) for tc in recovered):
                assistant.tool_calls = recovered
                assistant.text = None
        messages.append(_assistant_to_history(assistant))
        if not assistant.tool_calls:
            return assistant.text or ""
        # Döngü tespiti: aynı araç çağrısı imzası art arda tekrar ediyor mu?
        sig = tuple(
            (tc.name, json.dumps(tc.arguments, sort_keys=True))
            for tc in assistant.tool_calls
        )
        repeat = repeat + 1 if sig == last_sig else 0
        last_sig = sig
        step_error = False
        for tc in assistant.tool_calls:
            mutating = registry.is_mutating(tc.name)
            allowed, reason = is_allowed(tc.name, tc.arguments, mutating, mode, confirm)
            if allowed:
                with timed(log, "araç", id=turn_id, name=tc.name):
                    result = registry.execute(tc.name, tc.arguments)
            else:
                # İzin reddi HATA değil (model başarısızlığı sayılmaz → devretme tetiklemez).
                result = ToolResult(reason, ok=True)
                log.info("araç engellendi id=%s name=%s mode=%s", turn_id, tc.name, mode)
            if not result.ok:
                step_error = True
                log.warning("araç hatası id=%s name=%s: %s", turn_id, tc.name, result[:200])
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": _clip(str(result))}
            )
        err_streak = err_streak + 1 if step_error else 0
        # Devir tetikleyicileri: döngü ya da üst üste araç hatası.
        if escalate is not None and (repeat >= 2 or err_streak >= 2):
            return _escalate_and_record()
    # max_steps aşıldı: escalate varsa devret, yoksa hata ver.
    if escalate is not None:
        return _escalate_and_record()
    raise RuntimeError(f"max_steps ({max_steps}) aşıldı; model döngüde kaldı.")
