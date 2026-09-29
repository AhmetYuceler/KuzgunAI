from __future__ import annotations

from kuzgun.agent import run_turn
from kuzgun.models import OllamaClient
from kuzgun.tools import ToolRegistry
from kuzgun.tools.read_file import read_file, READ_FILE_SCHEMA
from kuzgun.tools.run_command import run_command, RUN_COMMAND_SCHEMA

SYSTEM_PROMPT = (
    "Sen Kuzgun'sun: Türkçe konuşan, yardımsever bir terminal asistanı. "
    "Gerektiğinde sana verilen araçları kullan. Emin olmadığın işlemde kullanıcıya sor."
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
    print("Kuzgun hazır. Çıkmak için /cikis")
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
