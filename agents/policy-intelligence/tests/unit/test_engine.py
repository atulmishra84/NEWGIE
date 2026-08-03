from policy_intelligence.domain.engine import determine_guardrails


def test_determines_p0_for_agent_stack(sample_bundle):
    recs, steps, conf = determine_guardrails(sample_bundle)
    assert recs
    ids = {r.guardrail_id for r in recs}
    assert "gr-prompt-injection" in ids
    assert "gr-tool-allowlist" in ids
    assert any(r.priority.value == "P0" for r in recs)
    assert steps
    assert conf.score > 0
