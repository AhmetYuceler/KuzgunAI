"""Betik workflow'ları (Faz C8): agent/parallel/pipeline; izole, yalnız son değer."""

from __future__ import annotations

from kuzgun.models import AssistantMessage
from kuzgun.workflows import Workflow, run_workflow


def test_agent_runs_isolated(make_engine):
    eng = make_engine([AssistantMessage(text="ajan cevabı", tool_calls=[])] * 3)
    wf = Workflow(eng)
    out = wf.agent("bir alt görev yap")
    assert out == "ajan cevabı"
    # İzole: ana konuşma etkilenmedi, geçici oturum temizlendi.
    assert not any("alt görev" in m.get("content", "") for m in eng.messages)
    assert eng._sessions == {}


def test_parallel_runs_all_and_preserves_order():
    wf = Workflow(engine=None)
    out = wf.parallel([lambda: 1, lambda: 2, lambda: 3])
    assert out == [1, 2, 3]


def test_pipeline_maps_stage_over_items():
    wf = Workflow(engine=None)
    assert wf.pipeline([1, 2, 3], lambda x: x * 10) == [10, 20, 30]


def test_run_workflow_returns_only_final_value(make_engine):
    eng = make_engine([AssistantMessage(text="x", tool_calls=[])] * 5)

    def script(wf):
        doubled = wf.pipeline([1, 2], lambda x: x + 1)  # ara değer bağlama girmez
        return {"sonuc": doubled}

    assert run_workflow(eng, script) == {"sonuc": [2, 3]}


def test_agent_with_schema_parses_json(make_engine):
    eng = make_engine([AssistantMessage(text='{"anahtar": "deger"}', tool_calls=[])] * 2)
    wf = Workflow(eng)
    out = wf.agent("json döndür", schema=True)
    assert out == {"anahtar": "deger"}
