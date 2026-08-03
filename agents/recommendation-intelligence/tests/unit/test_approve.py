import pytest
from gie_contracts.recommendation import RecommendationApproveRequest, RecommendationGenerateRequest, RecommendationStatus

@pytest.mark.asyncio
async def test_approve_marks_status(container, sample_bundle):
    report = await container.generate.handle(
        RecommendationGenerateRequest(bundle=sample_bundle), actor="t", correlation_id="c1"
    )
    rid = report.recommendations[0].recommendation_id
    updated = await container.approve.handle(
        RecommendationApproveRequest(tenant_id="acme", agent_id="agent-checkout-bot", recommendation_ids=[rid]),
        actor="approver",
        correlation_id="c2",
    )
    statuses = {i.recommendation_id: i.status for i in updated.recommendations}
    assert statuses[rid] == RecommendationStatus.APPROVED
