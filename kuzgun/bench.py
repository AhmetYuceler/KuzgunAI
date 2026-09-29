from __future__ import annotations

from collections import defaultdict

# Küçük, kategorili değerlendirme takımı (Kuzgun'un yerel modeli vs Claude).
DEFAULT_TASKS = [
    {"id": "bilgi1", "category": "bilgi", "prompt": "Fransa'nın başkenti neresidir?"},
    {"id": "bilgi2", "category": "bilgi", "prompt": "Fotosentez tek cümleyle nedir?"},
    {
        "id": "akil1",
        "category": "akil",
        "prompt": "Bir tren saatte 60 km hızla 2.5 saat giderse kaç km yol alır? Adım adım göster.",
    },
    {
        "id": "akil2",
        "category": "akil",
        "prompt": "Ali, Veli'den 3 yaş büyük. Veli 7 yaşında. 5 yıl sonra Ali kaç yaşında olur?",
    },
    {
        "id": "kod1",
        "category": "kod",
        "prompt": "Python'da bir listeyi tersine çevirmenin en kısa yolu nedir? Tek satır ver.",
    },
    {
        "id": "sohbet1",
        "category": "sohbet",
        "prompt": "Bugün biraz yorgunum ve motivasyonum düşük. Kısa bir moral verir misin?",
    },
]

_JUDGE_TEMPLATE = (
    "İki asistanın AYNI soruya verdiği cevabı karşılaştır ve hangisinin daha "
    "doğru, yardımcı ve net olduğunu seç.\n\n"
    "Soru: {question}\n\n"
    "Cevap A:\n{answer_a}\n\n"
    "Cevap B:\n{answer_b}\n\n"
    "SADECE tek kelime yaz: 'A', 'B' ya da 'tie' (berabere)."
)


def judge_pair(question: str, answer_a: str, answer_b: str, judge) -> str:
    """Bir hakem (Claude) ile iki cevabı karşılaştırır. 'A' / 'B' / 'tie' döner."""
    prompt = _JUDGE_TEMPLATE.format(
        question=question, answer_a=answer_a, answer_b=answer_b
    )
    verdict = (judge(prompt) or "").strip().lower()
    if "tie" in verdict or "berabere" in verdict or verdict.startswith("eşit"):
        return "tie"
    if verdict.startswith("a"):
        return "A"
    if verdict.startswith("b"):
        return "B"
    return "tie"


def run_benchmark(tasks, local_fn, claude_fn, judge) -> list[dict]:
    """Her görev için yerel (Kuzgun) ve Claude cevabını alır, hakemle (A/B yer
    değiştirmeli, konum yanlılığını azaltmak için) karşılaştırır, kazananı belirler."""
    results = []
    for t in tasks:
        a_local = local_fn(t["prompt"])
        a_claude = claude_fn(t["prompt"])
        # 1. tur: A=yerel, B=claude ; 2. tur: A=claude, B=yerel
        v1 = judge_pair(t["prompt"], a_local, a_claude, judge)
        v2 = judge_pair(t["prompt"], a_claude, a_local, judge)
        local_pts = (1 if v1 == "A" else 0) + (1 if v2 == "B" else 0)
        claude_pts = (1 if v1 == "B" else 0) + (1 if v2 == "A" else 0)
        if local_pts > claude_pts:
            winner = "kuzgun"
        elif claude_pts > local_pts:
            winner = "claude"
        else:
            winner = "tie"
        results.append(
            {
                "id": t["id"],
                "category": t["category"],
                "prompt": t["prompt"],
                "kuzgun": a_local,
                "claude": a_claude,
                "winner": winner,
            }
        )
    return results


def run_ab(tasks, a_fn, b_fn, judge, a_name: str = "A", b_name: str = "B") -> list[dict]:
    """C12: AYNI sistemin iki varyantını (ör. bir özellik açık vs kapalı) karşılaştırır.
    a_fn/b_fn(prompt)->cevap. Hakem A/B yer değiştirmeli sorulur (konum yanlılığı).
    Kazanan a_name / b_name / 'tie'. Her yeni özellik böyle ölçülür."""
    results = []
    for t in tasks:
        ans_a = a_fn(t["prompt"])
        ans_b = b_fn(t["prompt"])
        v1 = judge_pair(t["prompt"], ans_a, ans_b, judge)  # A=a, B=b
        v2 = judge_pair(t["prompt"], ans_b, ans_a, judge)  # A=b, B=a (swap)
        a_pts = (1 if v1 == "A" else 0) + (1 if v2 == "B" else 0)
        b_pts = (1 if v1 == "B" else 0) + (1 if v2 == "A" else 0)
        winner = a_name if a_pts > b_pts else b_name if b_pts > a_pts else "tie"
        results.append({
            "id": t["id"], "category": t.get("category", "genel"), "prompt": t["prompt"],
            a_name: ans_a, b_name: ans_b, "winner": winner,
        })
    return results


def summarize_ab(results: list[dict], a_name: str, b_name: str) -> dict:
    overall = {a_name: 0, b_name: 0, "tie": 0, "total": 0}
    by_cat: dict[str, dict] = defaultdict(lambda: {a_name: 0, b_name: 0, "tie": 0, "total": 0})
    for r in results:
        w = r["winner"]
        overall[w] = overall.get(w, 0) + 1
        overall["total"] += 1
        by_cat[r["category"]][w] = by_cat[r["category"]].get(w, 0) + 1
        by_cat[r["category"]]["total"] += 1
    return {"overall": overall, "by_category": dict(by_cat)}


def summarize(results: list[dict]) -> dict:
    overall = {"kuzgun": 0, "claude": 0, "tie": 0, "total": 0}
    by_cat: dict[str, dict] = defaultdict(
        lambda: {"kuzgun": 0, "claude": 0, "tie": 0, "total": 0}
    )
    for r in results:
        overall[r["winner"]] += 1
        overall["total"] += 1
        by_cat[r["category"]][r["winner"]] += 1
        by_cat[r["category"]]["total"] += 1
    return {"overall": overall, "by_category": dict(by_cat)}


def render_report(results: list[dict], summary: dict) -> str:
    """Sonuçları okunabilir bir Markdown raporuna çevirir."""
    o = summary["overall"]
    lines = ["# Kuzgun vs Claude — Değerlendirme Raporu\n"]
    lines.append(
        f"**Genel:** Kuzgun {o['kuzgun']} · Claude {o['claude']} · "
        f"Berabere {o['tie']} (toplam {o['total']} görev)\n"
    )
    lines.append("## Kategori bazında")
    lines.append("| Kategori | Kuzgun | Claude | Berabere |")
    lines.append("|---|---|---|---|")
    for cat, c in summary["by_category"].items():
        lines.append(f"| {cat} | {c['kuzgun']} | {c['claude']} | {c['tie']} |")
    lines.append("\n## Görev detayları")
    for r in results:
        lines.append(f"\n### [{r['category']}] {r['prompt']}")
        lines.append(f"**Kazanan:** {r['winner']}")
        lines.append(f"- **Kuzgun:** {r['kuzgun'][:400]}")
        lines.append(f"- **Claude:** {r['claude'][:400]}")
    return "\n".join(lines)


def _local_answerer():
    """Yerel modelin (araçsız, ham) tek atımlık cevabı — Claude'la adil kıyas için."""
    from kuzgun.engine import SYSTEM_PROMPT
    from kuzgun.models import OllamaClient

    client = OllamaClient()

    def answer(q: str) -> str:
        msg = client.chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": q},
            ],
            [],
        )
        return msg.text or ""

    return answer


def main() -> str:  # kuzgun-bench giriş noktası
    from kuzgun.teacher import ask_claude

    local = _local_answerer()
    results = run_benchmark(
        DEFAULT_TASKS, local_fn=local, claude_fn=ask_claude, judge=ask_claude
    )
    report = render_report(results, summarize(results))
    print(report)
    return report


if __name__ == "__main__":
    main()
