from gie_contracts.validation import ApprovalStatus, ValidationVerdict
from validation_intelligence.domain.engine import validate_policies


def test_validate_pass_path(sample_bundle):
    report = validate_policies(sample_bundle, run_simulation=True)
    assert report.verdict in {ValidationVerdict.PASS, ValidationVerdict.WARNING}
    assert report.approval_status in {
        ApprovalStatus.APPROVED,
        ApprovalStatus.APPROVED_WITH_WARNINGS,
    }
    cats = {c.category.value for c in report.checks}
    for required in [
        "syntax",
        "schema",
        "compliance",
        "runtime_compatibility",
        "policy_conflicts",
        "duplicate_rules",
        "performance",
        "security",
        "framework_compatibility",
        "model_compatibility",
        "simulation",
    ]:
        assert required in cats
    assert report.simulations
    assert report.summary


def test_detects_invalid_rego():
    from gie_contracts.validation import ValidationInputBundle

    bad = ValidationInputBundle(
        tenant_id="acme",
        content="allow { true }",
        filename="opa.rego",
        format="opa_rego",
    )
    report = validate_policies(bad, run_simulation=False)
    assert report.verdict == ValidationVerdict.FAILED
    assert report.approval_status == ApprovalStatus.REJECTED
    assert report.corrections
