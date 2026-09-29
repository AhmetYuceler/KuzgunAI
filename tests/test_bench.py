from kuzgun.bench import DEFAULT_TASKS, judge_pair, run_benchmark, summarize


def test_judge_pair_parses_verdict():
    assert judge_pair("s", "a", "b", judge=lambda p: "A") == "A"
    assert judge_pair("s", "a", "b", judge=lambda p: "B cevabı daha iyi") == "B"
    assert judge_pair("s", "a", "b", judge=lambda p: "berabere (tie)") == "tie"


def test_run_benchmark_tallies_with_ab_swap():
    tasks = [{"id": "t1", "category": "bilgi", "prompt": "soru"}]

    def judge(prompt):
        # 'Cevap A:' bölümünde YEREL varsa A kazansın (konum yanlılığına bağımsız)
        a_part = prompt.split("Cevap A:")[1].split("Cevap B:")[0]
        return "A" if "YEREL" in a_part else "B"

    res = run_benchmark(
        tasks,
        local_fn=lambda q: "YEREL cevap",
        claude_fn=lambda q: "CLAUDE cevap",
        judge=judge,
    )
    assert res[0]["winner"] == "kuzgun"


def test_summarize_counts():
    results = [
        {"id": "1", "category": "bilgi", "winner": "kuzgun"},
        {"id": "2", "category": "bilgi", "winner": "claude"},
        {"id": "3", "category": "kod", "winner": "tie"},
    ]
    s = summarize(results)
    assert s["overall"]["total"] == 3
    assert s["by_category"]["bilgi"]["kuzgun"] == 1
    assert s["by_category"]["bilgi"]["claude"] == 1


def test_default_tasks_have_categories():
    assert len(DEFAULT_TASKS) >= 4
    assert all("prompt" in t and "category" in t for t in DEFAULT_TASKS)
