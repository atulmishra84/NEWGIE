from gie_contracts.policy_generator import PolicyFormat, ValidationStatus
from policy_generator.domain.engine import generate_policy_package, validate_content

REQUIRED_FILES = {
    "guardrails.yaml",
    "guardrails.json",
    "opa.rego",
    "azure-foundry-policy.json",
    "openai-policy.json",
}


def test_generates_all_formats_with_metadata(sample_bundle):
    pkg = generate_policy_package(sample_bundle)
    assert len(pkg.policies) >= 18
    names = {p.filename for p in pkg.policies}
    assert REQUIRED_FILES.issubset(names)
    assert REQUIRED_FILES.issubset(set(pkg.named_artifacts))
    for p in pkg.policies:
        assert p.metadata.version
        assert p.metadata.source
        assert p.compliance_mapping is not None
        assert p.risk_mapping is not None
        assert p.validation.status in ValidationStatus
        assert p.rollback.steps
        assert p.content
    assert pkg.rollback.strategy
    assert pkg.summary


def test_validate_json_and_rego():
    ok = validate_content('{"a": 1}', PolicyFormat.JSON)
    assert ok.status == ValidationStatus.VALID
    bad = validate_content("{not-json", PolicyFormat.JSON)
    assert bad.status == ValidationStatus.INVALID
    rego = validate_content(
        "package gie.guardrails\n\nallow { true }\n", PolicyFormat.OPA_REGO
    )
    assert rego.status == ValidationStatus.VALID
