import pytest
from gie_contracts.compliance import (
    ComplianceAnalyzeRequest,
    ComplianceValidateRequest,
    ControlStatus,
    EvidenceItem,
)


@pytest.mark.asyncio
async def test_validate_improves_status(container, sample_bundle):
    first = await container.analyze.handle(
        ComplianceAnalyzeRequest(bundle=sample_bundle), actor="t", correlation_id="c1"
    )
    missing_before = sum(
        1 for a in first.assessments if a.status == ControlStatus.MISSING
    )
    assert missing_before > 0
    updated = await container.validate.handle(
        ComplianceValidateRequest(
            tenant_id="acme",
            application_id="app-health-bot",
            implemented_controls=["hipaa-phi-min", "gdpr-art32"],
            evidence=[
                EvidenceItem(
                    control_id="hipaa-phi-min",
                    title="Presidio PHI filter",
                    description="Runtime Presidio NER on outputs",
                    source="policy-agent",
                )
            ],
        ),
        actor="t",
        correlation_id="c2",
    )
    assert updated.report_id != first.report_id
    ids = {a.control_id: a.status for a in updated.assessments}
    assert ids.get("hipaa-phi-min") in {
        ControlStatus.IMPLEMENTED,
        ControlStatus.PARTIAL,
    }
