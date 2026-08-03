from orchestrator.domain.graph import default_analyze_workflow, sequential_analyze_workflow, topological_waves

def test_default_waves_parallelize_risk_compliance():
    wf = default_analyze_workflow(parallel_enabled=True)
    waves = topological_waves(wf)
    # find wave containing risk
    parallel = next(w for w in waves if any(s.step_id == "risk" for s in w))
    ids = {s.step_id for s in parallel}
    assert ids == {"risk", "compliance"}

def test_sequential_waves_are_singletons():
    wf = sequential_analyze_workflow()
    waves = topological_waves(wf)
    assert all(len(w) == 1 for w in waves)
    assert [w[0].step_id for w in waves] == [
        "context", "knowledge", "risk", "compliance", "policy",
        "recommendation", "generator", "validation", "explainability",
    ]
