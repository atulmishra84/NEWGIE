from gie_contracts.policy import OutputFormat, PolicyTarget

from policy_intelligence.domain.engine import determine_guardrails
from policy_intelligence.domain.generators import generate_artifacts


def test_generates_yaml_json_rego(sample_bundle):
    recs, _, _ = determine_guardrails(sample_bundle)
    arts = generate_artifacts(recs, sample_bundle)
    assert arts
    formats = {a.format for a in arts}
    assert OutputFormat.YAML in formats
    assert OutputFormat.JSON in formats or OutputFormat.VENDOR_NATIVE in formats
    assert OutputFormat.REGO in formats
    targets = {a.target for a in arts}
    assert PolicyTarget.OPENAI in targets
    assert PolicyTarget.OPA_REGO in targets
    opa = next(a for a in arts if a.target == PolicyTarget.OPA_REGO and a.format == OutputFormat.REGO)
    assert "package gie.policy" in opa.content
