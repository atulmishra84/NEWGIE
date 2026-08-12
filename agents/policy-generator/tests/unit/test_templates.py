from policy_generator.domain.templates import list_templates


def test_templates_cover_mission_formats():
    items = list_templates()
    assert len(items) >= 18
    filenames = {t.filename for t in items}
    assert "guardrails.yaml" in filenames
    assert "opa.rego" in filenames
    assert "openai-policy.json" in filenames
