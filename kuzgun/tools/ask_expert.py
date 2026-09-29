from __future__ import annotations

from kuzgun.teacher import ask_claude

ASK_EXPERT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "ask_expert",
        "description": (
            "Emin olmadığın, zor ya da güncel uzmanlık gerektiren bir soruda "
            "danışman uzmana (Claude) sorar ve cevabını döndürür. Yerel bilginle "
            "cevaplayamadığında kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Uzmana sorulacak soru."},
            },
            "required": ["question"],
        },
    },
}


def ask_expert(question: str, _runner=None) -> str:
    return ask_claude(question, _runner=_runner)
