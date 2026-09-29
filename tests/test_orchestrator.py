from kuzgun.models import AssistantMessage, FakeModelClient
from kuzgun.orchestrator import _plan_with_model, orchestrate


def test_orchestrate_runs_each_subtask_and_synthesizes():
    plan = lambda t: ["a1", "a2"]  # noqa: E731
    worker = lambda st: f"sonuç:{st}"  # noqa: E731
    synth = lambda t, results: " | ".join(f"{s}={r}" for s, r in results)  # noqa: E731
    out = orchestrate("görev", plan, worker, synth)
    assert out == "a1=sonuç:a1 | a2=sonuç:a2"


def test_orchestrate_empty_plan_falls_back_to_whole_task():
    out = orchestrate(
        "tekgörev",
        lambda t: [],
        lambda st: "r:" + st,
        lambda t, res: res[0][1],
    )
    assert out == "r:tekgörev"


def test_plan_parses_json_subtasks():
    client = FakeModelClient(
        [AssistantMessage(text='Plan: ["araştır X", "özetle X"]', tool_calls=[])]
    )
    subs = _plan_with_model("X araştır ve özetle", client)
    assert subs == ["araştır X", "özetle X"]


def test_plan_no_json_returns_empty():
    # C1: geçersiz çıktıda yeniden dener; hepsi başarısızsa [] döner (retries=2 → 3 deneme).
    client = FakeModelClient([AssistantMessage(text="düz metin", tool_calls=[])] * 3)
    assert _plan_with_model("görev", client) == []
