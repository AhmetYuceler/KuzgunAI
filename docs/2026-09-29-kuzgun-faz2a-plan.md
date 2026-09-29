# Kuzgun Faz 2a: İzin Kapısı + Modlar + Yerel Araçlar — Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kuzgun'a mod sistemi (plan/normal/otonom) ve izin kapısı kazandırmak; riskli araçları (dosya yazma, komut) moda göre gate'lemek; yerel araç setini genişletmek (write_file, glob, grep).

**Architecture:** Yeni `kuzgun/permissions.py` saf bir karar fonksiyonu (`is_allowed`) sağlar. `ToolRegistry` her araca bir `mutating` (değişiklik yapan) bayrağı ekler. `run_turn` her araç çağrısından önce izin kapısına danışır; izin yoksa aracı çalıştırmaz, gerekçeyi modele geri besler. CLI mod durumunu tutar, `/mod` slash komutlarıyla değiştirir, ve normal modda değişiklik yapan araçlar için kullanıcıya `e/h` onayı sorar.

**Tech Stack:** Python 3.12 (yeni bağımlılık yok — pathlib, glob, re stdlib), pytest.

**Spec:** `docs/2026-09-29-kuzgun-tasarim.md` (§8 Modlar & güvenlik)

## Global Constraints

- Python 3.12 venv (`.venv`); testler `.venv\Scripts\python.exe -m pytest`.
- Platform Windows 11.
- Modlar: `"plan"`, `"normal"`, `"otonom"` (küçük harf string).
- Kullanıcıya görünen metinler Türkçe; kod/parametre İngilizce.
- Değişiklik yapan araçlar (mutating): `write_file`, `run_command`. Okuyan araçlar: `read_file`, `glob_search`, `grep_search`.
- Güvenli varsayılan: `confirm` geri çağırması verilmemişse, normal modda değişiklik yapan araç **reddedilir** (sessizce çalıştırılmaz).
- `run_turn` geriye dönük uyumlu kalmalı: yeni parametreler (`mode`, `confirm`) varsayılanlı eklenir; mevcut çağrılar (`mode="normal"`, `confirm=None`) bozulmaz.

## Review Focus

- **Plan modunda değişiklik yapan araç** → çalıştırılmaz; gerekçe mesajı modele döner, döngü sürer. (Task 3 testi)
- **Normal modda değişiklik yapan araç, onay YOK** → reddedilir, araç çalışmaz. (Task 3 testi)
- **Normal modda değişiklik yapan araç, onay VAR** → çalışır. (Task 3 testi)
- **Okuyan araç her modda** → izin gerektirmez, çalışır. (Task 2/3 testi)
- **write_file var olmayan klasöre yazınca** → çökmez; klasörü oluşturur ya da `Error: ...` döndürür. (Task 4 testi)
- **grep geçersiz regex alınca** → çökmez, `Error: ...` döndürür. (Task 6 testi)

---

### Task 1: ToolRegistry'ye `mutating` bayrağı + ModelClient Protocol

**Files:**
- Modify: `kuzgun/tools/__init__.py`
- Modify: `kuzgun/models.py`
- Test: `tests/test_registry.py` (ekleme), `tests/test_models.py` (ekleme)

**Interfaces:**
- Produces:
  - `ToolRegistry.register(self, schema: dict, fn, mutating: bool = False) -> None`
  - `ToolRegistry.is_mutating(self, name: str) -> bool`
  - `kuzgun.models.ModelClient` — `typing.Protocol` (runtime_checkable) with `chat(self, messages, tools) -> AssistantMessage` (deferred minor #4'ü kapatır)

- [ ] **Step 1: Başarısız testleri yaz**

`tests/test_registry.py` sonuna ekle:
```python
def test_mutating_flag_defaults_false_and_can_be_set():
    reg = ToolRegistry()
    reg.register(SCHEMA, lambda text: text)                 # varsayilan: okuyan
    reg.register({"type": "function", "function": {"name": "yaz",
        "parameters": {"type": "object", "properties": {}}}},
        lambda: "ok", mutating=True)
    assert reg.is_mutating("echo") is False
    assert reg.is_mutating("yaz") is True

def test_is_mutating_unknown_is_false():
    assert ToolRegistry().is_mutating("yok") is False
```

`tests/test_models.py` sonuna ekle:
```python
def test_clients_satisfy_modelclient_protocol():
    from kuzgun.models import ModelClient
    assert isinstance(FakeModelClient([]), ModelClient)
```

- [ ] **Step 2: Testleri çalıştır, başarısız olduğunu gör**

Run: `.venv\Scripts\python.exe -m pytest tests/test_registry.py tests/test_models.py -v`
Expected: FAIL (`register() got unexpected keyword 'mutating'` / `is_mutating` yok / `ModelClient` import edilemiyor).

- [ ] **Step 3: Minimal implementasyonu yaz**

`kuzgun/tools/__init__.py` — `_tools` değerine mutating ekle:
```python
from __future__ import annotations

from typing import Callable


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, tuple[dict, Callable, bool]] = {}

    def register(self, schema: dict, fn: Callable, mutating: bool = False) -> None:
        name = schema["function"]["name"]
        self._tools[name] = (schema, fn, mutating)

    def schemas(self) -> list[dict]:
        return [schema for schema, _, _ in self._tools.values()]

    def is_mutating(self, name: str) -> bool:
        entry = self._tools.get(name)
        return bool(entry[2]) if entry else False

    def execute(self, name: str, arguments: dict) -> str:
        if name not in self._tools:
            return f"Error: unknown tool {name}"
        _, fn, _ = self._tools[name]
        try:
            result = fn(**arguments)
        except Exception as exc:
            return f"Error: {exc}"
        return str(result)
```

`kuzgun/models.py` — dosyanın başına (import'lardan sonra) Protocol ekle:
```python
from typing import Protocol, runtime_checkable
```
ve `AssistantMessage` tanımından sonra:
```python
@runtime_checkable
class ModelClient(Protocol):
    def chat(self, messages, tools) -> "AssistantMessage": ...
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini gör**

Run: `.venv\Scripts\python.exe -m pytest tests/test_registry.py tests/test_models.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add kuzgun/tools/__init__.py kuzgun/models.py tests/test_registry.py tests/test_models.py
git commit -m "feat: ToolRegistry mutating bayragi + ModelClient Protocol"
```

---

### Task 2: İzin kapısı (`permissions.is_allowed`)

**Files:**
- Create: `kuzgun/permissions.py`
- Test: `tests/test_permissions.py`

**Interfaces:**
- Produces:
  - `MODES: tuple[str, ...] = ("plan", "normal", "otonom")`
  - `is_allowed(name: str, arguments: dict, mutating: bool, mode: str, confirm=None) -> tuple[bool, str | None]`
    - `confirm: Callable[[str, dict], bool] | None`
    - Dönüş: (izin_var, gerekçe_mesajı_veya_None)

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_permissions.py`:
```python
from kuzgun.permissions import is_allowed


def test_read_tool_allowed_in_every_mode():
    for mode in ("plan", "normal", "otonom"):
        ok, msg = is_allowed("read_file", {}, mutating=False, mode=mode)
        assert ok is True and msg is None


def test_plan_mode_blocks_mutating():
    ok, msg = is_allowed("write_file", {}, mutating=True, mode="plan")
    assert ok is False and "plan" in msg.lower()


def test_normal_mode_mutating_denied_without_confirm():
    ok, msg = is_allowed("write_file", {}, mutating=True, mode="normal", confirm=None)
    assert ok is False


def test_normal_mode_mutating_allowed_when_confirmed():
    ok, msg = is_allowed("write_file", {}, mutating=True, mode="normal",
                         confirm=lambda name, args: True)
    assert ok is True and msg is None


def test_normal_mode_mutating_denied_when_rejected():
    ok, msg = is_allowed("write_file", {}, mutating=True, mode="normal",
                         confirm=lambda name, args: False)
    assert ok is False


def test_autonomous_mode_allows_mutating():
    ok, msg = is_allowed("run_command", {}, mutating=True, mode="otonom")
    assert ok is True
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

Run: `.venv\Scripts\python.exe -m pytest tests/test_permissions.py -v`
Expected: FAIL (ModuleNotFoundError: kuzgun.permissions).

- [ ] **Step 3: Minimal implementasyonu yaz**

`kuzgun/permissions.py`:
```python
from __future__ import annotations

from typing import Callable

MODES = ("plan", "normal", "otonom")


def is_allowed(
    name: str,
    arguments: dict,
    mutating: bool,
    mode: str,
    confirm: Callable[[str, dict], bool] | None = None,
) -> tuple[bool, str | None]:
    if not mutating or mode == "otonom":
        return True, None
    if mode == "plan":
        return False, (
            f"[plan modu] '{name}' değişiklik yapan bir araç; çalıştırılmadı. "
            "Uygulamak için: /mod normal"
        )
    # normal mod + değişiklik yapan araç -> onay iste
    approved = bool(confirm(name, arguments)) if confirm else False
    if approved:
        return True, None
    return False, f"[reddedildi] '{name}' için izin verilmedi."
```

- [ ] **Step 4: Testi çalıştır, geçtiğini gör**

Run: `.venv\Scripts\python.exe -m pytest tests/test_permissions.py -v`
Expected: PASS (6 test).

- [ ] **Step 5: Commit**

```powershell
git add kuzgun/permissions.py tests/test_permissions.py
git commit -m "feat: izin kapisi (plan/normal/otonom modlari)"
```

---

### Task 3: İzin kapısını `run_turn`'e entegre et

**Files:**
- Modify: `kuzgun/agent.py`
- Test: `tests/test_agent.py` (ekleme)

**Interfaces:**
- Produces:
  - `run_turn(client, messages, registry, mode: str = "normal", confirm=None, max_steps: int = 10) -> str`
  - İzin yoksa araç çalıştırılmaz; gerekçe mesajı `tool` sonucu olarak geçmişe eklenir; döngü sürer.

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_agent.py` sonuna ekle:
```python
def _spy_registry():
    """Cagrilinca kaydeden, degisiklik yapan (mutating) bir arac."""
    reg = ToolRegistry()
    calls = []
    schema = {"type": "function", "function": {"name": "yaz",
        "parameters": {"type": "object", "properties": {"x": {"type": "string"}}}}}
    reg.register(schema, lambda x="": calls.append(x) or "yazildi", mutating=True)
    return reg, calls


def test_plan_mode_blocks_mutating_tool():
    reg, calls = _spy_registry()
    client = FakeModelClient([
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "yaz", {"x": "a"})]),
        AssistantMessage(text="tamam", tool_calls=[]),
    ])
    messages = [{"role": "user", "content": "?"}]
    out = run_turn(client, messages, reg, mode="plan")
    assert out == "tamam"
    assert calls == []  # arac CALISMAMALI
    assert any("plan modu" in m.get("content", "").lower()
               for m in messages if m.get("role") == "tool")


def test_normal_mode_mutating_runs_when_confirmed():
    reg, calls = _spy_registry()
    client = FakeModelClient([
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "yaz", {"x": "a"})]),
        AssistantMessage(text="tamam", tool_calls=[]),
    ])
    out = run_turn(client, [{"role": "user", "content": "?"}], reg,
                   mode="normal", confirm=lambda n, a: True)
    assert calls == ["a"]  # arac CALISTI


def test_normal_mode_mutating_blocked_without_confirm():
    reg, calls = _spy_registry()
    client = FakeModelClient([
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "yaz", {"x": "a"})]),
        AssistantMessage(text="tamam", tool_calls=[]),
    ])
    run_turn(client, [{"role": "user", "content": "?"}], reg, mode="normal", confirm=None)
    assert calls == []
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent.py -v`
Expected: FAIL (`run_turn() got unexpected keyword 'mode'`).

- [ ] **Step 3: Minimal implementasyonu yaz**

`kuzgun/agent.py` — import ekle ve döngüyü güncelle:
```python
from __future__ import annotations

import json

from kuzgun.models import AssistantMessage
from kuzgun.permissions import is_allowed
from kuzgun.tools import ToolRegistry


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


def run_turn(
    client,
    messages: list[dict],
    registry: ToolRegistry,
    mode: str = "normal",
    confirm=None,
    max_steps: int = 10,
) -> str:
    for _ in range(max_steps):
        assistant = client.chat(messages, registry.schemas())
        messages.append(_assistant_to_history(assistant))
        if not assistant.tool_calls:
            return assistant.text or ""
        for tc in assistant.tool_calls:
            mutating = registry.is_mutating(tc.name)
            allowed, reason = is_allowed(tc.name, tc.arguments, mutating, mode, confirm)
            result = registry.execute(tc.name, tc.arguments) if allowed else reason
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": result}
            )
    raise RuntimeError(f"max_steps ({max_steps}) aşıldı; model döngüde kaldı.")
```

- [ ] **Step 4: Testi çalıştır, geçtiğini gör**

Run: `.venv\Scripts\python.exe -m pytest tests/test_agent.py -v`
Expected: PASS (mevcut 4 + yeni 3 = 7 test).

- [ ] **Step 5: Commit**

```powershell
git add kuzgun/agent.py tests/test_agent.py
git commit -m "feat: izin kapisini ajan dongusune entegre et (mode + confirm)"
```

---

### Task 4: `write_file` aracı

**Files:**
- Create: `kuzgun/tools/write_file.py`
- Test: `tests/test_write_file.py`

**Interfaces:**
- Produces:
  - `WRITE_FILE_SCHEMA: dict`
  - `write_file(path: str, content: str) -> str` (üst klasörleri oluşturur, hata yakalar)

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_write_file.py`:
```python
from pathlib import Path

from kuzgun.tools.write_file import write_file, WRITE_FILE_SCHEMA


def test_writes_file(tmp_path):
    f = tmp_path / "cikti.txt"
    out = write_file(str(f), "selam")
    assert Path(f).read_text(encoding="utf-8") == "selam"
    assert "selam" not in out.lower() or "yaz" in out.lower()  # onay mesaji dondurur


def test_creates_parent_dirs(tmp_path):
    f = tmp_path / "yeni" / "alt" / "not.txt"
    write_file(str(f), "veri")
    assert Path(f).read_text(encoding="utf-8") == "veri"


def test_schema_name():
    assert WRITE_FILE_SCHEMA["function"]["name"] == "write_file"
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

Run: `.venv\Scripts\python.exe -m pytest tests/test_write_file.py -v`
Expected: FAIL (import hatası).

- [ ] **Step 3: Minimal implementasyonu yaz**

`kuzgun/tools/write_file.py`:
```python
from __future__ import annotations

from pathlib import Path

WRITE_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": (
            "Bir dosyaya metin YAZAR (varsa üzerine yazar). Üst klasörler yoksa "
            "oluşturur. Kalıcı değişiklik yapar; dikkatli kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Yazılacak dosyanın yolu."},
                "content": {"type": "string", "description": "Dosyaya yazılacak metin."},
            },
            "required": ["path", "content"],
        },
    },
}


def write_file(path: str, content: str) -> str:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    except Exception as exc:
        return f"Error: {exc}"
    return f"Yazıldı: {path} ({len(content)} karakter)"
```

- [ ] **Step 4: Testi çalıştır, geçtiğini gör**

Run: `.venv\Scripts\python.exe -m pytest tests/test_write_file.py -v`
Expected: PASS (3 test).

- [ ] **Step 5: Commit**

```powershell
git add kuzgun/tools/write_file.py tests/test_write_file.py
git commit -m "feat: write_file araci"
```

---

### Task 5: `glob_search` aracı

**Files:**
- Create: `kuzgun/tools/glob_search.py`
- Test: `tests/test_glob_search.py`

**Interfaces:**
- Produces:
  - `GLOB_SCHEMA: dict`
  - `glob_search(pattern: str, root: str = ".") -> str` (eşleşen yolları satır satır döndürür)

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_glob_search.py`:
```python
from kuzgun.tools.glob_search import glob_search, GLOB_SCHEMA


def test_finds_matching_files(tmp_path):
    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "b.py").write_text("y", encoding="utf-8")
    (tmp_path / "c.txt").write_text("z", encoding="utf-8")
    out = glob_search("*.py", root=str(tmp_path))
    assert "a.py" in out and "b.py" in out
    assert "c.txt" not in out


def test_no_match_returns_message(tmp_path):
    out = glob_search("*.rs", root=str(tmp_path))
    assert "eşleşme" in out.lower() or out.strip() == "" or "yok" in out.lower()


def test_schema_name():
    assert GLOB_SCHEMA["function"]["name"] == "glob_search"
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

Run: `.venv\Scripts\python.exe -m pytest tests/test_glob_search.py -v`
Expected: FAIL (import hatası).

- [ ] **Step 3: Minimal implementasyonu yaz**

`kuzgun/tools/glob_search.py`:
```python
from __future__ import annotations

from pathlib import Path

GLOB_SCHEMA = {
    "type": "function",
    "function": {
        "name": "glob_search",
        "description": (
            "Bir desenle (glob) eşleşen dosyaları bulur. Örn desen: '*.py' veya "
            "'**/*.txt'. Bir klasörde hangi dosyalar var öğrenmek için kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob deseni, örn '**/*.py'."},
                "root": {"type": "string", "description": "Başlangıç klasörü. Varsayılan '.'."},
            },
            "required": ["pattern"],
        },
    },
}


def glob_search(pattern: str, root: str = ".") -> str:
    try:
        matches = sorted(str(p) for p in Path(root).glob(pattern))
    except Exception as exc:
        return f"Error: {exc}"
    if not matches:
        return "Eşleşme yok."
    return "\n".join(matches)
```

- [ ] **Step 4: Testi çalıştır, geçtiğini gör**

Run: `.venv\Scripts\python.exe -m pytest tests/test_glob_search.py -v`
Expected: PASS (3 test).

- [ ] **Step 5: Commit**

```powershell
git add kuzgun/tools/glob_search.py tests/test_glob_search.py
git commit -m "feat: glob_search araci"
```

---

### Task 6: `grep_search` aracı

**Files:**
- Create: `kuzgun/tools/grep_search.py`
- Test: `tests/test_grep_search.py`

**Interfaces:**
- Produces:
  - `GREP_SCHEMA: dict`
  - `grep_search(pattern: str, root: str = ".", glob: str = "**/*") -> str` (regex; `dosya:satır: içerik` döndürür; geçersiz regex'te `Error: ...`)

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_grep_search.py`:
```python
from kuzgun.tools.grep_search import grep_search, GREP_SCHEMA


def test_finds_pattern_in_files(tmp_path):
    (tmp_path / "a.txt").write_text("merhaba dünya\nikinci satır", encoding="utf-8")
    (tmp_path / "b.txt").write_text("baska içerik", encoding="utf-8")
    out = grep_search("dünya", root=str(tmp_path))
    assert "a.txt" in out and "merhaba dünya" in out
    assert "b.txt" not in out


def test_invalid_regex_returns_error(tmp_path):
    out = grep_search("(bozuk", root=str(tmp_path))
    assert out.startswith("Error:")


def test_schema_name():
    assert GREP_SCHEMA["function"]["name"] == "grep_search"
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

Run: `.venv\Scripts\python.exe -m pytest tests/test_grep_search.py -v`
Expected: FAIL (import hatası).

- [ ] **Step 3: Minimal implementasyonu yaz**

`kuzgun/tools/grep_search.py`:
```python
from __future__ import annotations

import re
from pathlib import Path

GREP_SCHEMA = {
    "type": "function",
    "function": {
        "name": "grep_search",
        "description": (
            "Dosyaların içinde bir düzenli ifade (regex) arar. Eşleşen satırları "
            "'dosya:satır: içerik' biçiminde döndürür. Kod/metin içinde bir şey "
            "aramak için kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Aranacak regex."},
                "root": {"type": "string", "description": "Başlangıç klasörü. Varsayılan '.'."},
                "glob": {"type": "string", "description": "Dosya deseni. Varsayılan '**/*'."},
            },
            "required": ["pattern"],
        },
    },
}


def grep_search(pattern: str, root: str = ".", glob: str = "**/*") -> str:
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        return f"Error: geçersiz regex: {exc}"
    results = []
    for path in Path(root).glob(glob):
        if not path.is_file():
            continue
        try:
            for i, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                if rx.search(line):
                    results.append(f"{path}:{i}: {line.strip()}")
        except Exception:
            continue
        if len(results) >= 200:
            break
    return "\n".join(results) if results else "Eşleşme yok."
```

- [ ] **Step 4: Testi çalıştır, geçtiğini gör**

Run: `.venv\Scripts\python.exe -m pytest tests/test_grep_search.py -v`
Expected: PASS (3 test).

- [ ] **Step 5: Commit**

```powershell
git add kuzgun/tools/grep_search.py tests/test_grep_search.py
git commit -m "feat: grep_search araci"
```

---

### Task 7: CLI'ye modlar + slash komutları + onay + yeni araçlar

**Files:**
- Modify: `kuzgun/cli.py`
- Test: `tests/test_cli.py` (ekleme)

**Interfaces:**
- Consumes: tüm araçlar, `run_turn(mode, confirm)`, `MODES`.
- Produces:
  - `build_default_registry()` artık 5 aracı kaydeder: read_file, write_file(mutating), run_command(mutating), glob_search, grep_search.
  - `handle_slash(line: str, state: dict) -> str | None` — `/mod ...`, `/yardim`, `/cikis` işler; slash değilse `None` döner.
  - `main()` mod durumunu tutar, slash komutlarını işler, normal modda onay sorar.

- [ ] **Step 1: Başarısız testleri yaz**

`tests/test_cli.py` sonuna ekle:
```python
from kuzgun.cli import build_default_registry, handle_slash


def test_default_registry_has_all_faz2_tools():
    reg = build_default_registry()
    names = [s["function"]["name"] for s in reg.schemas()]
    for t in ("read_file", "write_file", "run_command", "glob_search", "grep_search"):
        assert t in names


def test_mutating_tools_flagged():
    reg = build_default_registry()
    assert reg.is_mutating("write_file") is True
    assert reg.is_mutating("run_command") is True
    assert reg.is_mutating("read_file") is False


def test_slash_mod_changes_state():
    state = {"mode": "normal"}
    handle_slash("/mod plan", state)
    assert state["mode"] == "plan"


def test_slash_invalid_mode_keeps_state():
    state = {"mode": "normal"}
    out = handle_slash("/mod ucmaz", state)
    assert state["mode"] == "normal"
    assert out is not None  # kullaniciya uyari dondurur


def test_non_slash_returns_none():
    assert handle_slash("merhaba", {"mode": "normal"}) is None
```

- [ ] **Step 2: Testleri çalıştır, başarısız olduğunu gör**

Run: `.venv\Scripts\python.exe -m pytest tests/test_cli.py -v`
Expected: FAIL (`handle_slash` yok / yeni araçlar kayıtlı değil).

- [ ] **Step 3: Minimal implementasyonu yaz**

`kuzgun/cli.py`'yi güncelle:
```python
from __future__ import annotations

from kuzgun.agent import run_turn
from kuzgun.models import OllamaClient
from kuzgun.permissions import MODES
from kuzgun.tools import ToolRegistry
from kuzgun.tools.read_file import read_file, READ_FILE_SCHEMA
from kuzgun.tools.write_file import write_file, WRITE_FILE_SCHEMA
from kuzgun.tools.run_command import run_command, RUN_COMMAND_SCHEMA
from kuzgun.tools.glob_search import glob_search, GLOB_SCHEMA
from kuzgun.tools.grep_search import grep_search, GREP_SCHEMA

SYSTEM_PROMPT = (
    "Sen Kuzgun'sun: Türkçe konuşan, yardımsever bir terminal asistanı. "
    "Gerektiğinde sana verilen araçları kullan. Emin olmadığın işlemde kullanıcıya sor."
)


def build_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(READ_FILE_SCHEMA, read_file)
    reg.register(GLOB_SCHEMA, glob_search)
    reg.register(GREP_SCHEMA, grep_search)
    reg.register(WRITE_FILE_SCHEMA, write_file, mutating=True)
    reg.register(RUN_COMMAND_SCHEMA, run_command, mutating=True)
    return reg


def handle_slash(line: str, state: dict) -> str | None:
    """Slash komutunu işler. Slash değilse None döner."""
    if not line.startswith("/"):
        return None
    parts = line.split()
    cmd = parts[0]
    if cmd in ("/cikis", "/exit", "/quit"):
        state["quit"] = True
        return "Görüşürüz!"
    if cmd == "/yardim":
        return "Komutlar: /mod <plan|normal|otonom>, /yardim, /cikis"
    if cmd == "/mod":
        if len(parts) < 2:
            return f"Şu anki mod: {state['mode']}. Kullanım: /mod {'|'.join(MODES)}"
        yeni = parts[1]
        if yeni not in MODES:
            return f"Geçersiz mod: {yeni}. Seçenekler: {', '.join(MODES)}"
        state["mode"] = yeni
        return f"Mod değişti: {yeni}"
    return f"Bilinmeyen komut: {cmd}. /yardim yaz."


def _confirm(name: str, arguments: dict) -> bool:
    print(f"\n[onay] Kuzgun '{name}' çalıştırmak istiyor: {arguments}")
    ans = input("İzin veriyor musun? (e/h) ").strip().lower()
    return ans in ("e", "evet", "y", "yes")


def main() -> None:
    client = OllamaClient()
    registry = build_default_registry()
    state = {"mode": "normal", "quit": False}
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print(f"Kuzgun hazır (mod: {state['mode']}). /yardim ile komutlar, /cikis ile çık.")
    while True:
        try:
            user = input(f"\n[{state['mode']}] sen> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user:
            continue
        slash = handle_slash(user, state)
        if slash is not None:
            print(slash)
            if state["quit"]:
                break
            continue
        messages.append({"role": "user", "content": user})
        try:
            cevap = run_turn(client, messages, registry,
                             mode=state["mode"], confirm=_confirm)
        except Exception as exc:
            cevap = f"[hata] {exc}"
        print(f"\nkuzgun> {cevap}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Testleri çalıştır, geçtiğini gör**

Run: `.venv\Scripts\python.exe -m pytest tests/test_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Tüm suite yeşil**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: tüm testler PASS.

- [ ] **Step 6: Gerçek Ollama ile uçtan uca dene (manuel)**

```powershell
.\.venv\Scripts\Activate.ps1
kuzgun
```
Dene:
- `[normal] sen> /mod plan` → "Mod değişti: plan"
- `[plan] sen> masaüstüme deneme.txt oluştur içine merhaba yaz` → plan modunda **yazmamalı**, "plan modu" gerekçesini söylemeli.
- `[plan] sen> /mod normal` → geri dön.
- `[normal] sen> deneme.txt adında dosya oluştur içine 'selam' yaz` → **onay sormalı** (e/h); "e" deyince yazmalı.
- `[normal] sen> /mod otonom` → `bu klasorde *.py dosyalarini bul` → glob çalışmalı, sormadan.

- [ ] **Step 7: Commit**

```powershell
git add kuzgun/cli.py tests/test_cli.py
git commit -m "feat: CLI modlari, slash komutlari, onay akisi ve yeni araclar"
```

---

## Faz 2a sonunda elimizde ne var

- Kuzgun'un **modları** var: `/mod plan | normal | otonom`.
- **İzin kapısı** riskli araçları (write_file, run_command) moda göre gate'liyor; normal modda onay soruyor.
- Yeni araçlar: **write_file, glob_search, grep_search** (+ mevcut read_file, run_command).
- Hepsi test kapsamında; gerçek modelle doğrulanabilir.
- Sıradaki **Faz 2b:** web arama + sayfa okuma araçları (kendi planıyla).
