from validation_intelligence.domain.simulate import run_simulations

def test_simulation_denies_injection():
    docs = [{"filename": "x.json", "format": "json", "content": "{}", "body": {"rules": {"block_prompt_injection": True, "redact_pii": True, "tool_allowlist": True, "require_human_approval": True}}}]
    reports = run_simulations(docs)
    by_name = {r.scenario_name: r for r in reports}
    assert by_name["prompt_injection_attempt"].passed
    assert by_name["benign_user_query"].passed
