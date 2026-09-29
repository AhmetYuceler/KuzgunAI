from __future__ import annotations

from pathlib import Path

# Arama araçlarının atlaması gereken klasörler (bağımlılıklar, önbellek, vb.).
IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    ".superpowers",
}


def is_ignored(path: Path) -> bool:
    """Yol, atlanması gereken bir klasörün içindeyse True döner (.git, .venv, egg-info…)."""
    for part in path.parts:
        if part in IGNORE_DIRS or part.endswith(".egg-info"):
            return True
    return False
