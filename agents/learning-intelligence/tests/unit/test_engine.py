from gie_contracts.learning import KnowledgeChangeStatus
from learning_intelligence.domain.engine import run_learning_cycle

def test_learning_improves_and_proposes(sample_bundle):
    report = run_learning_cycle(sample_bundle, allow_auto_publish=False)
    assert report.feedback_consumed >= 5
    assert report.improved_recommendations
    rec = report.improved_recommendations[0]
    assert rec.confidence.previous_score is not None
    assert rec.changes
    assert report.drift_findings
    kinds = {d.kind for d in report.drift_findings}
    assert "new_attack_technique" in kinds or "regulation_change" in kinds or "policy_drift" in kinds
    assert report.policy_updates
    assert report.knowledge_changes
    assert all(k.status == KnowledgeChangeStatus.PROPOSED for k in report.knowledge_changes)
    assert all(k.requires_human_approval for k in report.knowledge_changes)
    assert report.summary
