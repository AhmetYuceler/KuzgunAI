"""/init — proje analizi ve KUZGUN.md üretimi (Claude Code'un /init'i gibi)."""

import os

from kuzgun.analyze import (
    NOTES_HEADER,
    build_chunks,
    extract_signatures,
    init_project,
    is_init_intent,
    load_project_notes,
    render_kuzgun_md,
    scan_project,
)


def _make_project(root):
    (root / "pyproject.toml").write_text(
        '[project]\nname = "ornek"\ndependencies = ["fastapi"]\n[project.scripts]\nornek = "ornek.cli:main"\n',
        encoding="utf-8",
    )
    (root / "README.md").write_text("# Örnek\n\nBu bir deneme projesi.\n", encoding="utf-8")
    pkg = root / "ornek"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "cli.py").write_text(
        "import os\n\nclass Uygulama:\n    def calistir(self):\n        pass\n\ndef main():\n    pass\n",
        encoding="utf-8",
    )
    (pkg / "web.js").write_text("export function render(x) {}\nclass Widget {}\n", encoding="utf-8")
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_cli.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    (root / ".venv").mkdir()
    (root / ".venv" / "big.py").write_text("x = 1\n" * 1000, encoding="utf-8")  # taranmamalı
    (root / "node_modules").mkdir()
    (root / "node_modules" / "m.js").write_text("junk", encoding="utf-8")


def test_scan_project_detects_stack_commands_and_files(tmp_path):
    _make_project(tmp_path)
    scan = scan_project(str(tmp_path))
    assert any("Python" in s for s in scan["stack"]) and "pyproject" in " ".join(scan["stack"])
    assert scan["name"] == "ornek"  # pyproject 'name' alanından
    assert any("ornek" in c for c in scan["commands"])  # pyproject scripts
    assert "Bu bir deneme projesi" in scan["readme"]
    paths = [f["path"] for f in scan["files"]]
    assert "ornek/cli.py" in paths and "tests/test_cli.py" in paths
    assert not any(p.startswith((".venv", "node_modules")) for p in paths)
    assert scan["tests_dir"] == "tests"
    assert scan["file_count"] >= 5 and "ornek/" in scan["tree"]


def test_extract_signatures_python_and_js():
    py = "import os\nclass A:\n    def m(self):\n        pass\ndef f(x, y):\n    return 1\n"
    assert extract_signatures("a.py", py) == ["class A:", "def m(self):", "def f(x, y):"]
    js = "export function render(x) {}\nconst y = 1;\nclass Widget {}\nexport default Widget\n"
    assert extract_signatures("a.js", js) == ["export function render(x) {}", "class Widget {}"]


def test_build_chunks_respects_size_limit(tmp_path):
    _make_project(tmp_path)
    scan = scan_project(str(tmp_path))
    chunks = build_chunks(scan, max_chars=80)
    assert len(chunks) >= 2
    assert all(len(c) <= 160 for c in chunks)  # tek blok sınırı aşabilir, iki blok asla


def test_render_preserves_user_notes_section():
    scan = {
        "name": "ornek", "root": "C:/p", "stack": ["Python (pyproject)"], "commands": ["pytest"],
        "tree": "ornek/\n  cli.py", "file_count": 3, "tests_dir": "tests", "readme": "", "files": [],
    }
    old = f"# eski\n\n{NOTES_HEADER}\n- kullanıcı notu: DB şeması değişmesin\n"
    md = render_kuzgun_md(scan, overview="Genel bakış metni", module_notes=["- cli.py: giriş"], previous=old)
    assert md.startswith("# ornek")
    assert "Genel bakış metni" in md and "cli.py: giriş" in md and "pytest" in md
    assert "DB şeması değişmesin" in md  # /hatirla benzeri notlar korunur
    assert md.count(NOTES_HEADER) == 1


def test_init_project_writes_kuzgun_md_with_model(tmp_path):
    _make_project(tmp_path)
    calls = []

    def model(prompt):
        calls.append(prompt)
        if "GENEL BAKIŞ" in prompt:
            return "ÖZET: genel"
        # 7B'nin şablonu harfiyen yazması taklit edilir: '- yol: ...' × dosya sayısı
        return "\n".join("- yol: ÖZET: parça" for _ in range(prompt.count("\n### ")))

    path, report = init_project(str(tmp_path), model, max_chars=400)
    assert os.path.basename(path) == "KUZGUN.md" and os.path.exists(path)
    text = open(path, encoding="utf-8").read()
    assert "# ornek" in text and "ÖZET: genel" in text and "ÖZET: parça" in text
    assert len(calls) >= 2  # en az bir parça + genel bakış
    assert "KUZGUN.md" in report and "dosya" in report
    # ikinci çalıştırma: notlar korunur
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n{NOTES_HEADER}\n- önemli: şema sabit\n")
    init_project(str(tmp_path), model, max_chars=400)
    assert "şema sabit" in open(path, encoding="utf-8").read()


def test_load_project_notes_reads_cwd_file(tmp_path):
    assert load_project_notes(str(tmp_path)) == ""
    (tmp_path / "KUZGUN.md").write_text("# p\nharita", encoding="utf-8")
    assert "harita" in load_project_notes(str(tmp_path))


def test_is_init_intent():
    assert is_init_intent("klasör içindeki tüm projeyi analiz et öğren")
    assert is_init_intent("bu projeyi incele ve yapısını öğren")
    assert is_init_intent("projeyi analiz et")
    assert not is_init_intent("şu fonksiyonu analiz et")
    assert not is_init_intent("merhaba")


def test_align_notes_fixes_template_lines_and_drops_junk():
    from kuzgun.analyze import _align_notes

    paths = ["a/x.py", "a/y.py"]
    assert _align_notes(["- yol: x işi", "- yol: y işi"], paths) == ["- a/x.py: x işi", "- a/y.py: y işi"]
    assert _align_notes(["- a/y.py: doğru", "- saçma satır"], paths) == ["- a/y.py: doğru"]
    assert _align_notes(["- a/x.py: bir", "- a/y.py: iki", "- Genel: fazla"], paths) == [
        "- a/x.py: bir", "- a/y.py: iki"
    ]


def test_chunks_skip_files_without_signatures(tmp_path):
    _make_project(tmp_path)
    chunks = build_chunks(scan_project(str(tmp_path)))
    joined = "\n".join(chunks)
    assert "### ornek/cli.py" in joined and "### ornek/__init__.py" not in joined


def test_align_notes_strips_cjk_garbage():
    from kuzgun.analyze import _align_notes

    out = _align_notes(["- a.py: giriş noktası登记验证已过期，请点击"], ["a.py"])
    assert out == ["- a.py: giriş noktası"]
