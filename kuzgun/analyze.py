"""/init — projeyi tara, parça parça özetlet, KUZGUN.md yaz (Claude Code'un /init'i).

Claude Code'da /init kod tabanını inceleyip CLAUDE.md üretir: derleme/test
komutları, mimari, önemli dosyalar, kurallar — böylece sonraki her oturum
projeyi tanıyarak başlar. Kuzgun'da aynı iş:

1. Tarama (kod, model değil): ağaç, dil/çerçeve, komutlar, README, dosya imzaları.
2. Özetleme (model, PARÇA PARÇA): 7B tek seferde büyük projeyi kavrayamıyor;
   imzalar küçük parçalara bölünür, her parça ayrı özetlenir, sonra genel bakış.
3. Yazma: proje klasörüne KUZGUN.md. Kullanıcının kendi notları (NOTES_HEADER
   altındaki bölüm) yeniden çalıştırmada korunur.
4. Yükleme: cli açılışta çalışma klasöründeki KUZGUN.md'yi engine'e
   extra_context olarak verir → her oturumda bağlamda.
"""

from __future__ import annotations

import os
import re

NOTES_HEADER = "## Notlar (kullanıcı — /init bunu korur)"
PROJECT_FILE = "KUZGUN.md"

_SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build", ".idea", ".vscode",
    "target", ".next", ".cache", "site-packages", "data",
}
_CODE_EXTS = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".jsx": "JavaScript", ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
    ".cs": "C#", ".rb": "Ruby", ".php": "PHP", ".c": "C", ".cpp": "C++", ".h": "C/C++",
    ".swift": "Swift", ".sql": "SQL", ".sh": "Shell", ".ps1": "PowerShell",
}
_MANIFESTS = {
    "pyproject.toml": "Python (pyproject)", "requirements.txt": "Python (requirements)",
    "setup.py": "Python (setup.py)", "package.json": "Node/JavaScript (package.json)",
    "Cargo.toml": "Rust (Cargo)", "go.mod": "Go (modules)", "pom.xml": "Java (Maven)",
    "build.gradle": "Java/Kotlin (Gradle)", "Gemfile": "Ruby (Bundler)",
    "composer.json": "PHP (Composer)", "Dockerfile": "Docker", "docker-compose.yml": "Docker Compose",
    "Makefile": "Makefile",
}
_SIG_RE = {
    "py": re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+\w+.*$"),
    "js": re.compile(
        r"^\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?(?:function\s+\w+|class\s+\w+)\b.*$"
    ),
    "go": re.compile(r"^\s*(?:func|type)\s+.*$"),
    "rs": re.compile(r"^\s*(?:pub\s+)?(?:fn|struct|enum|trait|impl)\s+.*$"),
    "generic": re.compile(r"^\s*(?:public|private|protected|static|class|def|function|func)\b.*$"),
}
_INIT_INTENT = re.compile(
    r"(proje|klasör|kod ?taban|repo)\w*.*\b(analiz|incele|öğren|ogren|tanı|tani|haritala)"
    r"|\b(analiz|incele|öğren|ogren)\w*.*\b(proje|klasör|kod ?taban|repo)",
    re.IGNORECASE,
)


def is_init_intent(message: str) -> bool:
    """'projeyi analiz et / klasörü öğren' gibi istekler → /init (7B bunu araçla
    kendi başına yapmıyor; deterministik rutine yönlendiririz)."""
    low = message.lower()
    return bool(_INIT_INTENT.search(low))


def extract_signatures(path: str, text: str, limit: int = 40) -> list[str]:
    """Dosyadan fonksiyon/sınıf imzalarını çıkarır (özet için yeter; gövde gerekmez)."""
    ext = os.path.splitext(path)[1].lower()
    key = {"py": (".py",), "js": (".js", ".ts", ".tsx", ".jsx"), "go": (".go",), "rs": (".rs",)}
    rx = _SIG_RE["generic"]
    for k, exts in key.items():
        if ext in exts:
            rx = _SIG_RE[k]
            break
    out = []
    for line in text.splitlines():
        if rx.match(line):
            out.append(line.strip().rstrip("{").strip() if ext == ".py" else line.strip())
            if len(out) >= limit:
                break
    return out


def _read_head(path: str, max_chars: int = 4000) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(max_chars)
    except OSError:
        return ""


def _commands(root: str, names: set[str]) -> list[str]:
    cmds: list[str] = []
    if "pyproject.toml" in names:
        text = _read_head(os.path.join(root, "pyproject.toml"), 20000)
        for m in re.finditer(r'^\s*([\w-]+)\s*=\s*"[\w.]+:\w+"', text, re.M):
            cmds.append(f"{m.group(1)}  (pyproject script)")
        if "pytest" in text:
            cmds.append("pytest  (testler)")
        if "ruff" in text:
            cmds.append("ruff check .  (lint)")
    if "package.json" in names:
        text = _read_head(os.path.join(root, "package.json"), 20000)
        m = re.search(r'"scripts"\s*:\s*\{(.*?)\}', text, re.S)
        if m:
            for k, v in re.findall(r'"([\w:-]+)"\s*:\s*"([^"]*)"', m.group(1)):
                cmds.append(f"npm run {k}  → {v[:60]}")
    if "Makefile" in names:
        text = _read_head(os.path.join(root, "Makefile"), 20000)
        for m in re.finditer(r"^([a-zA-Z_-]+):", text, re.M):
            cmds.append(f"make {m.group(1)}")
    if "Cargo.toml" in names:
        cmds += ["cargo build", "cargo test"]
    if "go.mod" in names:
        cmds += ["go build ./...", "go test ./..."]
    return cmds[:25]


def _project_name(root: str, names: set[str]) -> str:
    """Proje adı: pyproject/package.json 'name' alanı; yoksa klasör adı."""
    if "pyproject.toml" in names:
        m = re.search(r'^\s*name\s*=\s*"([^"]+)"', _read_head(os.path.join(root, "pyproject.toml"), 20000), re.M)
        if m:
            return m.group(1)
    if "package.json" in names:
        m = re.search(r'"name"\s*:\s*"([^"]+)"', _read_head(os.path.join(root, "package.json"), 20000))
        if m:
            return m.group(1)
    return ""


def scan_project(root: str, max_files: int = 60, max_tree: int = 80) -> dict:
    """Klasörü tarar; modele verilecek ham malzemeyi (ağaç, yığın, komutlar,
    README, dosya imzaları) üretir. Ağır dizinler (.venv, node_modules…) atlanır."""
    root = os.path.abspath(root)
    top = set(os.listdir(root)) if os.path.isdir(root) else set()
    stack = sorted({v for k, v in _MANIFESTS.items() if k in top})
    tree_lines: list[str] = []
    files: list[dict] = []
    langs: dict[str, int] = {}
    file_count = 0
    tests_dir = ""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS and not d.startswith("."))
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth > 4:
            dirnames[:] = []
            continue
        if rel != "." and len(tree_lines) < max_tree:
            tree_lines.append("  " * (depth - 1) + rel.replace(os.sep, "/").split("/")[-1] + "/")
        if not tests_dir and os.path.basename(dirpath).lower() in ("tests", "test", "__tests__", "spec"):
            tests_dir = rel.replace(os.sep, "/")
        for fn in sorted(filenames):
            ext = os.path.splitext(fn)[1].lower()
            file_count += 1
            if ext in _CODE_EXTS:
                langs[_CODE_EXTS[ext]] = langs.get(_CODE_EXTS[ext], 0) + 1
            if len(tree_lines) < max_tree and depth <= 1:
                tree_lines.append("  " * depth + fn)
            if ext in _CODE_EXTS and len(files) < max_files * 3:
                p = os.path.join(dirpath, fn)
                try:
                    size = os.path.getsize(p)
                except OSError:
                    size = 0
                files.append({"path": os.path.relpath(p, root).replace(os.sep, "/"), "size": size})
    # Büyük/önemli dosyalar önce (giriş noktaları ve büyük modüller özeti belirler).
    files.sort(key=lambda f: (-f["size"], f["path"]))
    files = files[:max_files]
    files.sort(key=lambda f: f["path"])
    for f in files:
        f["signatures"] = extract_signatures(f["path"], _read_head(os.path.join(root, f["path"]), 60000))
    for lang, n in sorted(langs.items(), key=lambda t: -t[1])[:4]:
        stack.append(f"{lang} ({n} dosya)")
    readme = ""
    for cand in ("README.md", "README.rst", "README.txt", "readme.md", "README"):
        if cand in top:
            readme = _read_head(os.path.join(root, cand), 3000)
            break
    return {
        "name": _project_name(root, top) or os.path.basename(root) or root,
        "root": root,
        "stack": stack,
        "commands": _commands(root, top),
        "tree": "\n".join(tree_lines),
        "file_count": file_count,
        "tests_dir": tests_dir,
        "readme": readme,
        "files": files,
    }


def build_chunks(scan: dict, max_chars: int = 5000) -> list[str]:
    """Dosya imzalarını modele sığacak parçalara böler (7B için küçük tutulur)."""
    chunks: list[str] = []
    cur = ""
    for f in scan["files"]:
        block = f"### {f['path']} ({f['size']} bayt)\n" + "\n".join(f["signatures"][:40]) + "\n\n"
        if cur and len(cur) + len(block) > max_chars:
            chunks.append(cur)
            cur = ""
        cur += block
    if cur:
        chunks.append(cur)
    return chunks


def _align_notes(lines: list[str], paths: list[str]) -> list[str]:
    """Modelin satırlarını gerçek dosya yollarıyla eşler. 7B bazen 'yol:' şablonunu
    harfiyen yazıyor ya da yolu atlıyor; satır sayısı dosya sayısına eşitse sırayla
    yol eklenir, değilse yalnız gerçek bir yol içeren satırlar tutulur."""
    known = set(paths)
    parsed = []
    for ln in lines:
        body = ln.lstrip("-").strip()
        head, _, rest = body.partition(":")
        parsed.append((head.strip(), rest.strip(), body))
    # Şablon modu: hiçbir satırda gerçek yol yok ama satır sayısı tutuyor → sırayla eşle.
    if len(lines) == len(paths) and not any(h in known for h, _, _ in parsed):
        out = []
        for path, (head, rest, body) in zip(paths, parsed):
            desc = rest if head.lower() in ("yol", "dosya", "path", "file") else body
            out.append(f"- {path}: {desc}")
        return out
    fixed: list[str] = []
    for head, rest, body in parsed:
        if head in known:
            fixed.append(f"- {head}: {rest}")
        elif any(p in body for p in paths):
            fixed.append(f"- {body}")
    return fixed


def _split_notes(previous: str | None) -> str:
    """Önceki KUZGUN.md'den kullanıcı notları bölümünü (NOTES_HEADER altı) alır."""
    if not previous or NOTES_HEADER not in previous:
        return ""
    return previous.split(NOTES_HEADER, 1)[1].strip()


def render_kuzgun_md(scan: dict, overview: str, module_notes: list[str], previous: str | None = None) -> str:
    notes = _split_notes(previous)
    parts = [
        f"# {scan['name']}",
        "",
        "_Kuzgun /init tarafından üretildi; her oturumda bağlama yüklenir. "
        "Kendi notlarını en alttaki 'Notlar' bölümüne yaz, /init onları korur._",
        "",
        "## Genel bakış",
        overview.strip() or "(özet üretilemedi)",
        "",
        "## Yığın",
        "\n".join(f"- {s}" for s in scan["stack"]) or "- (tespit edilemedi)",
        "",
        "## Komutlar",
        "\n".join(f"- {c}" for c in scan["commands"]) or "- (bulunamadı)",
        "",
        f"## Yapı ({scan['file_count']} dosya" + (f", testler: {scan['tests_dir']}" if scan.get("tests_dir") else "") + ")",
        "```",
        scan["tree"],
        "```",
        "",
        "## Modüller (nerede ne var)",
        "\n".join(module_notes) or "- (yok)",
        "",
        NOTES_HEADER,
        notes,
        "",
    ]
    return "\n".join(parts)


def init_project(root: str, model_fn, max_chars: int = 5000, progress=None) -> tuple[str, str]:
    """Taramayı yapar, parçaları modele özetletir, KUZGUN.md yazar.

    model_fn(prompt) -> str : tek seferlik, araçsız model çağrısı.
    progress(msg)           : isteğe bağlı ilerleme bildirimi.
    Dönüş: (dosya yolu, kullanıcıya rapor).
    """
    say = progress or (lambda m: None)
    scan = scan_project(root)
    say(f"tarandı: {scan['file_count']} dosya, {len(scan['files'])} kod dosyası imzalandı")
    chunks = build_chunks(scan, max_chars=max_chars)
    module_notes: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        say(f"özetleniyor: parça {i}/{len(chunks)}")
        paths = re.findall(r"^### (\S+) \(", chunk, re.M)
        ornek = paths[0] if paths else "src/app.py"
        prompt = (
            f"Proje: {scan['name']}. Aşağıda {len(paths)} kaynak dosyanın yolu ve içindeki "
            "fonksiyon/sınıf imzaları var. Her dosya için, verilen SIRAYLA, tek satır yaz. "
            f"Satır biçimi tam olarak şöyle (dosya yolunu AYNEN kopyala):\n- {ornek}: ne işe yarar "
            "(en önemli 2-3 öğe)\nUydurma; yalnız imzalardan çıkarılabileni yaz. Türkçe. "
            "Başka hiçbir şey yazma.\n\n" + chunk
        )
        out = (model_fn(prompt) or "").strip()
        lines = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("-")]
        module_notes.extend(_align_notes(lines, paths))
    say("genel bakış yazılıyor")
    overview_prompt = (
        "GENEL BAKIŞ: Aşağıdaki bilgilerden bu projenin ne olduğunu, ana bileşenlerini ve "
        "bir değişiklik yaparken nereden başlanacağını 5-8 cümleyle Türkçe anlat. Uydurma.\n\n"
        f"Yığın: {', '.join(scan['stack'])}\nKomutlar: {'; '.join(scan['commands'][:10])}\n"
        f"README (baş):\n{scan['readme'][:1500]}\n\nModül notları:\n" + "\n".join(module_notes[:80])
    )
    overview = (model_fn(overview_prompt) or "").strip()
    path = os.path.join(scan["root"], PROJECT_FILE)
    previous = _read_head(path, 200000) if os.path.exists(path) else None
    md = render_kuzgun_md(scan, overview, module_notes, previous)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    report = (
        f"{PROJECT_FILE} yazıldı: {path}\n"
        f"{scan['file_count']} dosya tarandı, {len(scan['files'])} kod dosyası {len(chunks)} parçada özetlendi. "
        "Bu klasörde Kuzgun her açıldığında bu harita bağlama yüklenir."
    )
    return path, report


def load_project_notes(root: str) -> str:
    """Çalışma klasöründeki KUZGUN.md (varsa) — engine'e extra_context olarak verilir."""
    return _read_head(os.path.join(root, PROJECT_FILE), 30000)
