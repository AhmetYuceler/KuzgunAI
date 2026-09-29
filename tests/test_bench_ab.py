"""Özellik açık/kapalı A/B değerlendirmesi (Faz C12)."""

from __future__ import annotations

from kuzgun.bench import run_ab, summarize_ab


def _judge_prefers(keyword):
    # Hangi cevap keyword içeriyorsa onu seçen sahte hakem (konum-bağımsız).
    def judge(prompt):
        # prompt içinde 'Cevap A:' ve 'Cevap B:' bloklarından hangisinde keyword var?
        a_part = prompt.split("Cevap A:")[1].split("Cevap B:")[0]
        b_part = prompt.split("Cevap B:")[1]
        if keyword in a_part and keyword not in b_part:
            return "A"
        if keyword in b_part and keyword not in a_part:
            return "B"
        return "tie"
    return judge


def test_run_ab_picks_better_variant():
    tasks = [{"id": "t1", "category": "genel", "prompt": "soru?"}]
    # A varyantı iyi cevap, B kötü.
    results = run_ab(
        tasks,
        a_fn=lambda q: "bu çok iyi bir cevap",
        b_fn=lambda q: "vasat cevap",
        judge=_judge_prefers("iyi"),
        a_name="acik",
        b_name="kapali",
    )
    assert results[0]["winner"] == "acik"


def test_summarize_ab_counts_by_variant():
    results = [
        {"winner": "acik", "category": "x"},
        {"winner": "acik", "category": "x"},
        {"winner": "kapali", "category": "y"},
        {"winner": "tie", "category": "y"},
    ]
    s = summarize_ab(results, "acik", "kapali")
    assert s["overall"]["acik"] == 2
    assert s["overall"]["kapali"] == 1
    assert s["overall"]["tie"] == 1
    assert s["overall"]["total"] == 4
