from __future__ import annotations

import json
import os
import re
import time
import uuid

from kuzgun.logging_setup import get_logger, timed
from kuzgun.models import AssistantMessage, ToolCall
from kuzgun.permissions import is_allowed
from kuzgun.tools import ToolRegistry, ToolResult

log = get_logger("agent")

# Kullanıcıya "ne yapıyor" göstermek için araç → Türkçe eylem etiketi (canlı durum barı).
_TOOL_LABELS = {
    "web_search": "🔍 internette araştırıyor",
    "fetch_url": "🌐 web sayfası okunuyor",
    "read_file": "📄 dosya okuyor",
    "write_file": "✍️ dosya yazıyor",
    "run_command": "⚙️ komut çalıştırıyor",
    "glob_search": "🔎 dosyalar aranıyor",
    "grep_search": "🔎 içerikte aranıyor",
    "ask_expert": "🧠 uzmana (Claude) danışıyor",
    "remember": "📝 not alıyor",
    "media_control": "🎵 medya kontrol",
    "weather": "🌤️ hava durumu alınıyor",
    "web_recon": "🌐 site inceleniyor (keşif)",
    "security_scan": "🛡️ zafiyet taranıyor",
}


def _tool_label(name: str) -> str:
    return _TOOL_LABELS.get(name, f"⚙️ {name} çalıştırıyor") + "…"


# Araç → çağrıdaki "önemli" argümanın adı. Kalıcı aktivite satırında bu değer
# gösterilir (ör. run_command · git status, read_file · kuzgun/cli.py). Claude
# Code'un tool-call kartlarındaki gibi "neyle çalıştırdığını" kullanıcı görür.
_ARG_KEYS = {
    "web_search": "query",
    "grep_search": "pattern",
    "glob_search": "pattern",
    "read_file": "path",
    "write_file": "path",
    "run_command": "command",
    "fetch_url": "url",
    "web_recon": "url",
    "security_scan": "target",
    "weather": "city",
    "media_control": "action",
    "ask_expert": "question",
    "remember": "text",
}


def _arg_summary(name: str, arguments: dict, limit: int = 60) -> str:
    """Aktivite satırında gösterilecek kısa argüman özeti. Adlandırılmış anahtar
    (yol/komut/sorgu…) öncelikli; yoksa ilk basit değer; hiçbiri yoksa boş.
    Satır sonları boşluğa çevrilir, limit karakterde kesilir (tek satır kalsın)."""
    key = _ARG_KEYS.get(name)
    val = arguments.get(key) if key and key in arguments else None
    if val is None:
        for v in arguments.values():
            if isinstance(v, (str, int, float, bool)):
                val = v
                break
    if val is None:
        return ""
    s = " ".join(str(val).split())
    return s[:limit] + ("…" if len(s) > limit else "")


def _tool_activity(name: str, arguments: dict) -> str:
    """Kalıcı 'ne yapıyor' satırının metni: emoji etiketi + kısa argüman."""
    base = _TOOL_LABELS.get(name, f"⚙️ {name} çalıştırıyor")
    arg = _arg_summary(name, arguments)
    return f"{base} · {arg}" if arg else base


def _oneline(text, limit: int = 80) -> str:
    """Metnin ilk boş olmayan satırını kırparak döndürür (sonuç özetleri için)."""
    first = next((ln for ln in str(text).splitlines() if ln.strip()), "").strip()
    return first[:limit] + ("…" if len(first) > limit else "")


def _result_summary(result, seconds: float | None = None) -> str:
    """Araç sonucunun tek satırlık özeti: ✓/✗ + ilk satır (+ satır sayısı [+ süre])."""
    text = str(result)
    ok = getattr(result, "ok", True)
    body = _oneline(text)
    n = len([ln for ln in text.splitlines() if ln.strip()])
    if n > 1:
        body = f"{body}  ({n} satır)"
    if seconds is not None and seconds >= 0.05:
        body = f"{body}  {seconds:.1f}sn"
    return f"{'✓' if ok else '✗'} {body}".rstrip()


# B6: araç çıktısı bağlamı doldurmasın; bundan uzunsa kırpılıp geçmişe öyle girer.
MAX_TOOL_CHARS = 4000

# Kullanıcı ESC/Ctrl+C ile turu iptal edince dönen metin (öğrenmeye/yansıtmaya girmez).
CANCELLED = "[iptal edildi]"


def _clip(text: str, limit: int = MAX_TOOL_CHARS) -> str:
    """Uzun araç çıktısını baş+son koruyarak kırpar (7B'nin küçük bağlamı için)."""
    if len(text) <= limit:
        return text
    head = text[: limit // 2]
    tail = text[-limit // 4 :]
    atlanan = len(text) - len(head) - len(tail)
    return f"{head}\n... [{atlanan} karakter kırpıldı] ...\n{tail}"


def _render_result(text: str, out_dir: str | None = None, limit: int = MAX_TOOL_CHARS) -> str:
    """Araç çıktısını bağlama hazırlar (C3). Limitten kısaysa aynen; uzunsa:
    - out_dir verildiyse TAM çıktı dosyaya yazılır, bağlama önizleme + dosya yolu girer
      (7B gerekirse read_file ile tamamını okur — veri kaybolmaz);
    - out_dir yoksa baş+son kırpılır (_clip)."""
    if len(text) <= limit:
        return text
    if out_dir:
        try:
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, f"cikti-{uuid.uuid4().hex[:8]}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            preview = text[: limit // 2]
            return (
                f"{preview}\n... [çıktı uzun ({len(text)} karakter). TAM çıktı dosyada: "
                f"{path} — gerekirse read_file ile oku] ..."
            )
        except Exception as exc:  # noqa: BLE001 — dosyaya yazılamazsa kırpmaya düş
            log.warning("araç çıktısı dosyaya yazılamadı: %s", exc)
    return _clip(text, limit)


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


def _coerce(v: str):
    """XML/metin argüman değerini uygun türe çevirir (sayı/bool, yoksa dize)."""
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    if v in ("true", "True"):
        return True
    if v in ("false", "False"):
        return False
    return v


_XML_FUNC_RE = re.compile(r"<function=([a-zA-Z_]\w*)>")
_XML_PARAM_RE = re.compile(
    r"<parameter=([a-zA-Z_]\w*)>\s*(.*?)\s*"
    r"(?=<parameter=|</parameter>|</function>|</tool_call>|<function=|$)",
    re.DOTALL,
)


def _xml_tool_calls(text: str | None) -> list[ToolCall]:
    """Qwen3-Coder'ın XML araç-çağrısı biçimini metinden kurtarır:

        <tool_call><function=read_file>
        <parameter=path> /a/b.py </parameter>
        <parameter=max_bytes> 100000 </parameter>
        </function></tool_call>

    Ollama şablonu bunu gerçek tool_call'a çeviremediğinde model cevabı içinde
    METİN olarak sızar; ayrıştırmazsak Kuzgun bunu 'cevap' sanıp turu bitirir.
    Kapanış etiketleri eksik olsa da (model sık atlar) tolere eder. Her <function=>
    bloğunu ve onu izleyen <parameter=> çiftlerini toplar."""
    if not text or "<function=" not in text:
        return []
    calls: list[ToolCall] = []
    funcs = list(_XML_FUNC_RE.finditer(text))
    for i, fm in enumerate(funcs):
        name = fm.group(1)
        start = fm.end()
        end = funcs[i + 1].start() if i + 1 < len(funcs) else len(text)
        block = text[start:end]
        args = {pm.group(1): _coerce(pm.group(2).strip()) for pm in _XML_PARAM_RE.finditer(block)}
        calls.append(ToolCall(id=f"xml-{i + 1}", name=name, arguments=args))
    return calls


def extract_tool_calls_from_text(text: str | None) -> list[ToolCall]:
    """Model, araç çağrısını gerçek çağrı yerine METİN olarak verirse yakalar:
    Qwen3-Coder XML biçimi, JSON nesnesi ya da `func(arg=...)` sözde-çağrısı.
    Küçük/kod modellerinin sık yaptığı format hatasını telafi eder.
    """
    if not text:
        return []
    xml = _xml_tool_calls(text)  # Qwen3-Coder XML biçimi önce
    if xml:
        return xml
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
    wrapup: bool = False,
    out_dir: str | None = None,
    rules=(),
    on_step=None,
    max_tool_chars: int = MAX_TOOL_CHARS,
    cancel=None,
) -> str:
    """Ajan döngüsü. `escalate` verilirse model döngüye girer / araçlar üst üste hata
    verir / max_steps aşılırsa uzmana (Claude) devreder. `wrapup=True` ise max_steps
    dolunca çökmek/Claude'a gitmek yerine modelden kısa bir 'yaptıklarını özetle'
    turu istenir (C2: bütçe bitince zarif kapanış, yarım kalma yerine kısmi cevap)."""
    def _escalate_and_record() -> str:
        # A3 (bug #5): devredilen cevabı geçmişe de yaz ki sonraki turda kaybolmasın.
        (on_step or (lambda *a, **k: None))("🧠 uzmana (Claude) danışıyor…", kind="tool")
        reply = escalate(_last_user_text(messages))
        messages.append({"role": "assistant", "content": reply})
        return reply

    def _budget_wrapup() -> str:
        messages.append({
            "role": "system",
            "content": (
                "Adım bütçen doldu. Yeni araç ÇAĞIRMA. Şimdiye dek yaptıklarını kısaca "
                "özetle ve elde ettiğin en iyi KISMİ cevabı ver; neyin eksik kaldığını da söyle."
            ),
        })
        with timed(log, "wrapup", id=turn_id):
            final = client.chat(messages, [])
        text = final.text or ""
        messages.append({"role": "assistant", "content": text})
        log.info("bütçe doldu → zarif kapanış id=%s", turn_id)
        return text

    step_cb = on_step or (lambda *a, **k: None)
    turn_id = uuid.uuid4().hex[:8]
    log.info("tur başladı id=%s mode=%s", turn_id, mode)
    last_sig = None
    repeat = 0
    err_streak = 0
    for step in range(max_steps):
        # ESC/Ctrl+C: her adımın başında iptal kontrolü → tüm bütçe bitene kadar
        # beklemeden, çalışan tur adımlar arasında durur.
        if cancel is not None and cancel():
            log.info("tur iptal edildi id=%s adım=%s", turn_id, step)
            return CANCELLED
        step_cb("düşünüyor…" if step == 0 else f"devam ediyor (adım {step + 1})…")
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
            # Kalıcı "ne yapıyor" satırı (soru altına yazılır): araç + argüman.
            step_cb(_tool_activity(tc.name, tc.arguments), kind="tool")
            mutating = registry.is_mutating(tc.name)
            allowed, reason = is_allowed(tc.name, tc.arguments, mutating, mode, confirm, rules=rules)
            if allowed:
                t0 = time.perf_counter()
                with timed(log, "araç", id=turn_id, name=tc.name):
                    result = registry.execute(tc.name, tc.arguments)
                # ✓/✗ sonuç özeti + geçen süre (Claude Code'daki gibi).
                step_cb(_result_summary(result, time.perf_counter() - t0), kind="result")
            else:
                # İzin reddi HATA değil (model başarısızlığı sayılmaz → devretme tetiklemez).
                result = ToolResult(reason, ok=True)
                step_cb("⛔ " + _oneline(reason), kind="result")
                log.info("araç engellendi id=%s name=%s mode=%s", turn_id, tc.name, mode)
            if not result.ok:
                step_error = True
                log.warning("araç hatası id=%s name=%s: %s", turn_id, tc.name, result[:200])
            messages.append(
                {"role": "tool", "tool_call_id": tc.id,
                 "content": _render_result(str(result), out_dir, max_tool_chars)}
            )
        err_streak = err_streak + 1 if step_error else 0
        # Döngü ya da üst üste araç hatası: varsa uzmana devret; yoksa modele
        # döngüde olduğunu söyleyip kır (aynı dosyayı 5 kez okuma vakası).
        if repeat >= 2 or err_streak >= 2:
            if escalate is not None:
                return _escalate_and_record()
            messages.append({
                "role": "system",
                "content": (
                    "Aynı aracı aynı argümanlarla tekrar tekrar çağırıyorsun ve sonucu "
                    "zaten aldın. Bir daha AYNI çağrıyı yapma; ya farklı bir adım at ya da "
                    "eldeki bilgiyle kullanıcıya cevabı ver."
                ),
            })
            repeat = 0
            err_streak = 0
            last_sig = None
    # max_steps aşıldı. Öncelik: zarif kapanış (istenmişse) → devretme → hata.
    if wrapup:
        return _budget_wrapup()
    if escalate is not None:
        return _escalate_and_record()
    raise RuntimeError(f"max_steps ({max_steps}) aşıldı; model döngüde kaldı.")
