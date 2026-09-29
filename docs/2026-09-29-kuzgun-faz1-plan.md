# Kuzgun Faz 1: Kurulum + Çekirdek Ajan Döngüsü — Uygulama Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Yerel modele (Ollama + Qwen2.5-7B) bağlanan, araç çağırıp sonucuyla cevap üretebilen, test edilebilir bir çekirdek ajan iskeleti kurmak.

**Architecture:** Python paketi `kuzgun/`. Model erişimi bir `ModelClient` arayüzünün arkasında (gerçek: `OllamaClient`; testler: `FakeModelClient`). Ajan döngüsü normalize edilmiş tiplerle (`AssistantMessage`, `ToolCall`) çalışır, geçmişi OpenAI-uyumlu formatta tutar. Araçlar bir `ToolRegistry`'de kayıtlı; her araç şeması + fonksiyonu. Böylece döngü ve araçlar canlı model olmadan birim-test edilir.

**Tech Stack:** Python 3.12, `openai` SDK (Ollama'nın OpenAI-uyumlu API'sine konuşmak için), `pytest`, Ollama, Qwen2.5-7B-Instruct (Q4_K_M).

**Spec:** `docs/2026-09-29-kuzgun-tasarim.md`

## Global Constraints

- Python **3.12** (sistemdeki 3.14 değil) — ayrı venv `.venv/` içinde.
- Platform: **Windows 11**, PowerShell. Komut çalıştırma `shell=True` ile.
- Model istemcisi Ollama'ya `http://localhost:11434/v1` üzerinden bağlanır; `api_key="ollama"` (yer tutucu, doğrulanmaz).
- Yerel model varsayılanı: `qwen2.5:7b-instruct`.
- Araç seçimi **`auto`** (Ollama `tool_choice: required` desteklemez — döngü buna göre tasarlanır).
- Kullanıcıya görünen metinler **Türkçe**; kod/parametre adları İngilizce.
- Bağımlılıklar minimum: yalnızca `openai` ve `pytest` (bu fazda başka paket yok).
- Ajan döngüsünde sonsuz döngüye karşı **`max_steps` (varsayılan 10)** sınırı zorunlu.

## Review Focus

- **Var olmayan dosya yolu** → `read_file` çökmez, `Error: ...` döndürür. (Task 5 testi)
- **Başarısız/uzun süren komut** → `run_command` çökmez; hata çıktısını ve zaman aşımını yakalar. (Task 6 testi)
- **Bilinmeyen araç adı** modelden gelirse → `ToolRegistry.execute` `Error: unknown tool ...` döndürür, döngü devam eder. (Task 4 testi)
- **Bozuk/eksik araç argümanları** → `execute` `TypeError`'ı yakalar, `Error: ...` döndürür. (Task 4 testi)
- **Model sürekli araç çağırırsa (sonsuz döngü)** → `max_steps` aşılınca kontrollü `RuntimeError`. (Task 4 testi)

---

### Task 1: Proje iskeleti + Python 3.12 ortamı

**Files:**
- Create: `pyproject.toml`
- Create: `kuzgun/__init__.py`
- Create: `tests/__init__.py`
- Create: `.gitignore`

**Interfaces:**
- Produces: çalışan bir venv, kurulu `openai` + `pytest`, `kuzgun` paketi import edilebilir.

- [ ] **Step 1: Python 3.12'yi kur (yoksa)**

PowerShell:
```powershell
winget install --id Python.Python.3.12 -e --source winget
```
Kuruluysa atla. Doğrula: `py -3.12 --version` → `Python 3.12.x`.

- [ ] **Step 2: Sanal ortam oluştur ve etkinleştir**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version   # 3.12.x beklenir
```

- [ ] **Step 3: `pyproject.toml` yaz**

```toml
[project]
name = "kuzgun"
version = "0.1.0"
description = "Kişisel terminal yapay zeka ajanı"
requires-python = ">=3.12"
dependencies = ["openai>=1.40"]

[project.optional-dependencies]
dev = ["pytest>=8"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["kuzgun*"]
```

- [ ] **Step 4: `.gitignore` yaz**

```gitignore
.venv/
__pycache__/
*.pyc
data/
.pytest_cache/
```

- [ ] **Step 5: Boş paket dosyalarını oluştur**

`kuzgun/__init__.py`:
```python
__version__ = "0.1.0"
```
`tests/__init__.py`: (boş dosya)

- [ ] **Step 6: Bağımlılıkları kur**

```powershell
pip install -e ".[dev]"
```

- [ ] **Step 7: İskeleti doğrula**

```powershell
python -c "import kuzgun; print(kuzgun.__version__)"
pytest -q
```
Beklenen: sürüm yazılır; pytest "no tests ran" (hata değil).

- [ ] **Step 8: Commit** (git kurulmuşsa; değilse önce `git init`)

```powershell
git add pyproject.toml kuzgun/__init__.py tests/__init__.py .gitignore
git commit -m "chore: proje iskeleti ve Python 3.12 ortami"
```

---

### Task 2: Ollama + model kurulumu ve hız ölçümü

**Files:** (kod yok — ortam kurulumu ve doğrulama)

**Interfaces:**
- Produces: `localhost:11434` üzerinde çalışan, `qwen2.5:7b-instruct` modeli yüklü bir Ollama.

- [ ] **Step 1: Ollama'yı kur**

```powershell
winget install --id Ollama.Ollama -e --source winget
```
Alternatif: https://ollama.com/download adresinden indir. Kurulum sonrası yeni bir terminal aç.

- [ ] **Step 2: Ollama servisini doğrula**

```powershell
ollama --version
curl http://localhost:11434/api/tags
```
Beklenen: sürüm; boş `models` listesi (JSON).

- [ ] **Step 3: Modeli indir**

```powershell
ollama pull qwen2.5:7b-instruct
```

- [ ] **Step 4: Hızı ölç (gerçek tok/s)**

```powershell
ollama run qwen2.5:7b-instruct --verbose "Merhaba, kendini bir cumleyle tanit."
```
`eval rate` satırındaki tokens/s değerini not et. Beklenen: ~35-55 tok/s. Belirgin düşükse (GPU'ya sığmıyorsa) `ollama ps` ile GPU/CPU dağılımını kontrol et.

- [ ] **Step 5: OpenAI-uyumlu uç noktayı doğrula**

```powershell
curl http://localhost:11434/v1/chat/completions -H "Content-Type: application/json" -d '{\"model\":\"qwen2.5:7b-instruct\",\"messages\":[{\"role\":\"user\",\"content\":\"tek kelime: merhaba\"}]}'
```
Beklenen: `choices[0].message.content` içeren JSON.

---

### Task 3: Model istemcisi arayüzü + normalize tipler + Fake

**Files:**
- Create: `kuzgun/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces:
  - `@dataclass ToolCall(id: str, name: str, arguments: dict)`
  - `@dataclass AssistantMessage(text: str | None, tool_calls: list[ToolCall])`
  - `class OllamaClient: def chat(self, messages: list[dict], tools: list[dict] | None) -> AssistantMessage`
  - `class FakeModelClient: __init__(self, scripted: list[AssistantMessage]); def chat(...) -> AssistantMessage` (her çağrıda sıradaki scripted mesajı döndürür)

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_models.py`:
```python
from kuzgun.models import AssistantMessage, ToolCall, FakeModelClient

def test_fake_client_returns_scripted_messages_in_order():
    scripted = [
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "read_file", {"path": "x"})]),
        AssistantMessage(text="bitti", tool_calls=[]),
    ]
    client = FakeModelClient(scripted)
    first = client.chat(messages=[], tools=[])
    assert first.tool_calls[0].name == "read_file"
    second = client.chat(messages=[], tools=[])
    assert second.text == "bitti"
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

Run: `pytest tests/test_models.py -v`
Expected: FAIL (ImportError: cannot import name ...).

- [ ] **Step 3: Minimal implementasyonu yaz**

`kuzgun/models.py`:
```python
from __future__ import annotations
import json
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class AssistantMessage:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


class FakeModelClient:
    """Testler için: önceden yazılmış mesajları sırayla döndürür."""

    def __init__(self, scripted: list[AssistantMessage]):
        self._scripted = list(scripted)
        self._i = 0

    def chat(self, messages, tools) -> AssistantMessage:
        msg = self._scripted[self._i]
        self._i += 1
        return msg


class OllamaClient:
    """Ollama'nin OpenAI-uyumlu API'sine baglanir."""

    def __init__(
        self,
        model: str = "qwen2.5:7b-instruct",
        base_url: str = "http://localhost:11434/v1",
    ):
        from openai import OpenAI

        self._client = OpenAI(base_url=base_url, api_key="ollama")
        self._model = model

    def chat(self, messages, tools) -> AssistantMessage:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools or None,
            temperature=0.2,
        )
        m = resp.choices[0].message
        tool_calls = []
        for tc in (m.tool_calls or []):
            args = tc.function.arguments or "{}"
            tool_calls.append(
                ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(args))
            )
        return AssistantMessage(text=m.content, tool_calls=tool_calls)
```

- [ ] **Step 4: Testi çalıştır, geçtiğini gör**

Run: `pytest tests/test_models.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add kuzgun/models.py tests/test_models.py
git commit -m "feat: model istemcisi arayuzu, normalize tipler ve fake client"
```

---

### Task 4: Araç kayıt defteri (ToolRegistry)

**Files:**
- Create: `kuzgun/tools/__init__.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Consumes: —
- Produces:
  - `class ToolRegistry`
    - `register(self, schema: dict, fn) -> None` (schema OpenAI-function formatı)
    - `schemas(self) -> list[dict]`
    - `execute(self, name: str, arguments: dict) -> str` (bilinmeyen araç ve fonksiyon hatalarını `Error: ...` metnine çevirir)

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_registry.py`:
```python
from kuzgun.tools import ToolRegistry

SCHEMA = {
    "type": "function",
    "function": {
        "name": "echo",
        "description": "Verilen metni geri dondurur.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
}

def test_register_and_execute():
    reg = ToolRegistry()
    reg.register(SCHEMA, lambda text: f"echo: {text}")
    assert reg.execute("echo", {"text": "selam"}) == "echo: selam"
    assert reg.schemas()[0]["function"]["name"] == "echo"

def test_unknown_tool_returns_error():
    reg = ToolRegistry()
    assert reg.execute("yok", {}).startswith("Error: unknown tool")

def test_bad_arguments_returns_error():
    reg = ToolRegistry()
    reg.register(SCHEMA, lambda text: text)
    # 'text' eksik -> TypeError yakalanmali
    assert reg.execute("echo", {}).startswith("Error:")
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

Run: `pytest tests/test_registry.py -v`
Expected: FAIL (ModuleNotFoundError: kuzgun.tools).

- [ ] **Step 3: Minimal implementasyonu yaz**

`kuzgun/tools/__init__.py`:
```python
from __future__ import annotations
from typing import Callable


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, tuple[dict, Callable]] = {}

    def register(self, schema: dict, fn: Callable) -> None:
        name = schema["function"]["name"]
        self._tools[name] = (schema, fn)

    def schemas(self) -> list[dict]:
        return [schema for schema, _ in self._tools.values()]

    def execute(self, name: str, arguments: dict) -> str:
        if name not in self._tools:
            return f"Error: unknown tool {name}"
        _, fn = self._tools[name]
        try:
            result = fn(**arguments)
        except Exception as exc:  # bozuk argüman, çalışma hatası vb.
            return f"Error: {exc}"
        return str(result)
```

- [ ] **Step 4: Testi çalıştır, geçtiğini gör**

Run: `pytest tests/test_registry.py -v`
Expected: PASS (3 test).

- [ ] **Step 5: Commit**

```powershell
git add kuzgun/tools/__init__.py tests/test_registry.py
git commit -m "feat: arac kayit defteri (ToolRegistry) + hata yakalama"
```

---

### Task 5: `read_file` aracı

**Files:**
- Create: `kuzgun/tools/read_file.py`
- Test: `tests/test_read_file.py`

**Interfaces:**
- Produces:
  - `READ_FILE_SCHEMA: dict`
  - `read_file(path: str, max_bytes: int = 100_000) -> str`

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_read_file.py`:
```python
from kuzgun.tools.read_file import read_file, READ_FILE_SCHEMA

def test_reads_existing_file(tmp_path):
    f = tmp_path / "not.txt"
    f.write_text("selam dunya", encoding="utf-8")
    assert read_file(str(f)) == "selam dunya"

def test_missing_file_returns_error(tmp_path):
    assert read_file(str(tmp_path / "yok.txt")).startswith("Error:")

def test_schema_name():
    assert READ_FILE_SCHEMA["function"]["name"] == "read_file"
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

Run: `pytest tests/test_read_file.py -v`
Expected: FAIL (import hatası).

- [ ] **Step 3: Minimal implementasyonu yaz**

`kuzgun/tools/read_file.py`:
```python
from __future__ import annotations
from pathlib import Path

READ_FILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": (
            "Yerel dosya sisteminden bir dosyanin metnini okur. Bir dosyanin "
            "icerigini gormek/incelemek gerektiginde kullan. Mutlak yol ver. "
            "Kodu calistirmaz, sadece metni dondurur."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Okunacak dosyanin yolu."},
                "max_bytes": {
                    "type": "integer",
                    "description": "Okunacak azami karakter. Varsayilan 100000.",
                },
            },
            "required": ["path"],
        },
    },
}


def read_file(path: str, max_bytes: int = 100_000) -> str:
    p = Path(path)
    if not p.is_file():
        return f"Error: dosya bulunamadi: {path}"
    text = p.read_text(encoding="utf-8", errors="replace")
    return text[:max_bytes]
```

- [ ] **Step 4: Testi çalıştır, geçtiğini gör**

Run: `pytest tests/test_read_file.py -v`
Expected: PASS (3 test).

- [ ] **Step 5: Commit**

```powershell
git add kuzgun/tools/read_file.py tests/test_read_file.py
git commit -m "feat: read_file araci"
```

---

### Task 6: `run_command` aracı

**Files:**
- Create: `kuzgun/tools/run_command.py`
- Test: `tests/test_run_command.py`

**Interfaces:**
- Produces:
  - `RUN_COMMAND_SCHEMA: dict`
  - `run_command(command: str, timeout: int = 30) -> str` (stdout+stderr birleşik; zaman aşımı ve hata yakalanır)

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_run_command.py`:
```python
from kuzgun.tools.run_command import run_command, RUN_COMMAND_SCHEMA

def test_runs_simple_command():
    out = run_command("echo merhaba")
    assert "merhaba" in out

def test_timeout_returns_error():
    # 30sn beklemeyi 1sn zaman asimiyla kes
    out = run_command("ping -n 30 127.0.0.1", timeout=1)
    assert "Error:" in out or "zaman" in out.lower()

def test_schema_name():
    assert RUN_COMMAND_SCHEMA["function"]["name"] == "run_command"
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

Run: `pytest tests/test_run_command.py -v`
Expected: FAIL (import hatası).

- [ ] **Step 3: Minimal implementasyonu yaz**

`kuzgun/tools/run_command.py`:
```python
from __future__ import annotations
import subprocess

RUN_COMMAND_SCHEMA = {
    "type": "function",
    "function": {
        "name": "run_command",
        "description": (
            "Bir kabuk (shell) komutu calistirir ve ciktisini dondurur. Script "
            "calistirmak, derlemek, test etmek veya sistem bilgisi almak icin kullan. "
            "Kalici degisiklik yapabilir; dikkatli kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Calistirilacak komut."},
                "timeout": {
                    "type": "integer",
                    "description": "Saniye cinsinden zaman asimi. Varsayilan 30.",
                },
            },
            "required": ["command"],
        },
    },
}


def run_command(command: str, timeout: int = 30) -> str:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Error: komut {timeout} saniyede zaman asimina ugradi."
    except Exception as exc:
        return f"Error: {exc}"
    out = proc.stdout
    if proc.returncode != 0:
        out += f"\n[cikis kodu {proc.returncode}]\n{proc.stderr}"
    return out.strip()
```

- [ ] **Step 4: Testi çalıştır, geçtiğini gör**

Run: `pytest tests/test_run_command.py -v`
Expected: PASS (3 test).

- [ ] **Step 5: Commit**

```powershell
git add kuzgun/tools/run_command.py tests/test_run_command.py
git commit -m "feat: run_command araci (zaman asimi + hata yakalama)"
```

---

### Task 7: Ajan döngüsü (agent loop)

**Files:**
- Create: `kuzgun/agent.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- Consumes: `ModelClient.chat`, `ToolRegistry.execute/schemas`, `AssistantMessage`, `ToolCall`.
- Produces:
  - `run_turn(client, messages: list[dict], registry: ToolRegistry, max_steps: int = 10) -> str`
  - Döngü: model araç isterse çalıştırır, sonucu geçmişe ekler, tekrar sorar; model metin dönünce onu döndürür. `max_steps` aşılırsa `RuntimeError`.

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_agent.py`:
```python
import pytest
from kuzgun.agent import run_turn
from kuzgun.models import AssistantMessage, ToolCall, FakeModelClient
from kuzgun.tools import ToolRegistry

def _registry_with_echo():
    reg = ToolRegistry()
    schema = {"type": "function", "function": {"name": "echo",
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}}
    reg.register(schema, lambda text: f"ARAC: {text}")
    return reg

def test_direct_answer_without_tools():
    client = FakeModelClient([AssistantMessage(text="direkt cevap", tool_calls=[])])
    out = run_turn(client, [{"role": "user", "content": "selam"}], ToolRegistry())
    assert out == "direkt cevap"

def test_calls_tool_then_answers():
    client = FakeModelClient([
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "echo", {"text": "x"})]),
        AssistantMessage(text="arac calisti", tool_calls=[]),
    ])
    messages = [{"role": "user", "content": "echo x"}]
    out = run_turn(client, messages, _registry_with_echo())
    assert out == "arac calisti"
    # gecmiste bir tool sonucu bulunmali
    assert any(m.get("role") == "tool" and "ARAC: x" in m.get("content", "") for m in messages)

def test_unknown_tool_does_not_crash():
    client = FakeModelClient([
        AssistantMessage(text=None, tool_calls=[ToolCall("1", "yok", {})]),
        AssistantMessage(text="devam", tool_calls=[]),
    ])
    out = run_turn(client, [{"role": "user", "content": "?"}], ToolRegistry())
    assert out == "devam"

def test_max_steps_guard():
    # surekli arac isteyen model -> RuntimeError
    loop_msg = AssistantMessage(text=None, tool_calls=[ToolCall("1", "echo", {"text": "x"})])
    client = FakeModelClient([loop_msg] * 20)
    with pytest.raises(RuntimeError):
        run_turn(client, [{"role": "user", "content": "?"}], _registry_with_echo(), max_steps=3)
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

Run: `pytest tests/test_agent.py -v`
Expected: FAIL (ImportError: run_turn).

- [ ] **Step 3: Minimal implementasyonu yaz**

`kuzgun/agent.py`:
```python
from __future__ import annotations
import json
from kuzgun.models import AssistantMessage
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


def run_turn(client, messages: list[dict], registry: ToolRegistry, max_steps: int = 10) -> str:
    for _ in range(max_steps):
        assistant = client.chat(messages, registry.schemas())
        messages.append(_assistant_to_history(assistant))
        if not assistant.tool_calls:
            return assistant.text or ""
        for tc in assistant.tool_calls:
            result = registry.execute(tc.name, tc.arguments)
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": result}
            )
    raise RuntimeError(f"max_steps ({max_steps}) asildi; model dongude kaldi.")
```

- [ ] **Step 4: Testi çalıştır, geçtiğini gör**

Run: `pytest tests/test_agent.py -v`
Expected: PASS (4 test).

- [ ] **Step 5: Commit**

```powershell
git add kuzgun/agent.py tests/test_agent.py
git commit -m "feat: cekirdek ajan dongusu (tool_use loop + max_steps)"
```

---

### Task 8: Minimal `kuzgun` CLI + gerçek Ollama ile uçtan uca doğrulama

**Files:**
- Create: `kuzgun/cli.py`
- Modify: `pyproject.toml` (console script ekle)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `run_turn`, `OllamaClient`, `ToolRegistry`, araç şemaları/fonksiyonları.
- Produces:
  - `build_default_registry() -> ToolRegistry` (read_file + run_command kayıtlı)
  - `SYSTEM_PROMPT: str`
  - `main() -> None` (basit REPL: kullanıcıdan satır al, `run_turn` çağır, cevabı yaz; `/cikis` ile biter)

- [ ] **Step 1: Başarısız testi yaz**

`tests/test_cli.py`:
```python
from kuzgun.cli import build_default_registry

def test_default_registry_has_core_tools():
    names = [s["function"]["name"] for s in build_default_registry().schemas()]
    assert "read_file" in names
    assert "run_command" in names
```

- [ ] **Step 2: Testi çalıştır, başarısız olduğunu gör**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL (ImportError).

- [ ] **Step 3: Minimal implementasyonu yaz**

`kuzgun/cli.py`:
```python
from __future__ import annotations
from kuzgun.agent import run_turn
from kuzgun.models import OllamaClient
from kuzgun.tools import ToolRegistry
from kuzgun.tools.read_file import read_file, READ_FILE_SCHEMA
from kuzgun.tools.run_command import run_command, RUN_COMMAND_SCHEMA

SYSTEM_PROMPT = (
    "Sen Kuzgun'sun: Turkce konusan, yardimsever bir terminal asistani. "
    "Gerektiginde sana verilen araclari kullan. Emin olmadigin islemde kullaniciya sor."
)


def build_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(READ_FILE_SCHEMA, read_file)
    reg.register(RUN_COMMAND_SCHEMA, run_command)
    return reg


def main() -> None:
    client = OllamaClient()
    registry = build_default_registry()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("Kuzgun hazir. Cikmak icin /cikis")
    while True:
        try:
            user = input("\nsen> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user in ("/cikis", "/exit", "/quit"):
            break
        if not user:
            continue
        messages.append({"role": "user", "content": user})
        try:
            cevap = run_turn(client, messages, registry)
        except Exception as exc:
            cevap = f"[hata] {exc}"
        print(f"\nkuzgun> {cevap}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: `pyproject.toml`'a console script ekle**

`[project]` bloğundan sonra ekle:
```toml
[project.scripts]
kuzgun = "kuzgun.cli:main"
```
Sonra: `pip install -e ".[dev]"` (script'i kaydetmek için).

- [ ] **Step 5: Testi çalıştır, geçtiğini gör**

Run: `pytest tests/test_cli.py -v`
Expected: PASS.

- [ ] **Step 6: Tüm testleri çalıştır**

Run: `pytest -q`
Expected: tüm testler PASS.

- [ ] **Step 7: Gerçek Ollama ile uçtan uca dene (manuel)**

Ollama çalışırken:
```powershell
kuzgun
```
Sırayla dene:
- `sen> merhaba, kendini tanit` → Türkçe cevap gelmeli (araçsız).
- `sen> bu klasordeki pyproject.toml dosyasini oku ve icinde hangi python surumu yaziyor soyle` → `read_file` çağırıp cevap vermeli.
- `sen> 'python --version' komutunu calistir ve ciktisini soyle` → `run_command` çağırmalı.
Beklenen: model doğru aracı seçip sonucu kullanıyor. Seçmiyorsa Faz 2'de sistem promptu/araç açıklamaları güçlendirilecek (not al).

- [ ] **Step 8: Commit**

```powershell
git add kuzgun/cli.py tests/test_cli.py pyproject.toml
git commit -m "feat: minimal kuzgun CLI + varsayilan arac kaydi"
```

---

## Faz 1 sonunda elimizde ne var

- `kuzgun` komutu terminalde açılıyor, yerel modelle (Qwen2.5-7B) konuşuyor.
- Model, `read_file` ve `run_command` araçlarını çağırıp sonucuyla cevap verebiliyor.
- Ajan döngüsü, araçlar ve kayıt defteri tam birim-test kapsamında (canlı model olmadan).
- Sonraki faz (Faz 2): daha fazla araç (dosya yaz, glob/grep, web arama) + izin kapısı + modlar. Kendi planıyla gelecek.
