from __future__ import annotations

import json
import re

_PLAN_SYSTEM = (
    "Sen bir görev yöneticisisin. Verilen görevi 2-5 BAĞIMSIZ alt-göreve böl "
    "(her biri tek başına yapılabilsin). SADECE bir JSON dizisi döndür, başka "
    'hiçbir şey yazma. Örnek: ["ilk alt görev", "ikinci alt görev"].'
)

_SYNTH_SYSTEM = (
    "Sen bir yöneticisin. Alt-görevlerin sonuçlarını birleştirip kullanıcıya "
    "tek, net ve düzenli bir cevap ver."
)


def _extract_json_array(text: str) -> list[str] | None:
    m = re.search(r"\[.*\]", text or "", re.DOTALL)
    if not m:
        return None
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return None
    if isinstance(arr, list):
        return [str(x) for x in arr]
    return None


def _plan_with_model(task: str, client) -> list[str]:
    """Modeli 'yönetici' olarak kullanıp görevi alt-görevlere böler."""
    msg = client.chat(
        [
            {"role": "system", "content": _PLAN_SYSTEM},
            {"role": "user", "content": task},
        ],
        [],
    )
    return _extract_json_array(msg.text or "") or []


def _synth_with_model(task: str, results: list[tuple[str, str]], client) -> str:
    parts = "\n".join(f"- {st}:\n{res}" for st, res in results)
    msg = client.chat(
        [
            {"role": "system", "content": _SYNTH_SYSTEM},
            {"role": "user", "content": f"Görev: {task}\n\nAlt-görev sonuçları:\n{parts}"},
        ],
        [],
    )
    return msg.text or ""


def orchestrate(task: str, plan_fn, worker_fn, synth_fn) -> str:
    """Görevi böl → her alt-görevi bir işçi-ajan yapsın → sonuçları birleştir.

    plan_fn(task)->list[str], worker_fn(subtask)->str, synth_fn(task, results)->str.
    Plan boşsa görevin tamamı tek alt-görev sayılır (hiçbir şey atlanmaz)."""
    subtasks = plan_fn(task) or [task]
    results: list[tuple[str, str]] = []
    for st in subtasks:
        results.append((st, worker_fn(st)))
    return synth_fn(task, results)
