from gie_contracts.recommendation import Audience, Priority, RecommendationCategory
from recommendation_intelligence.domain.engine import generate_recommendations


def test_generates_prioritized_recommendations(sample_bundle):
    report = generate_recommendations(sample_bundle)
    assert report.recommendations
    assert report.counts["total"] == len(report.recommendations)
    assert report.executive_recommendations
    assert report.developer_recommendations
    assert report.security_team_recommendations
    assert report.platform_team_recommendations
    for item in report.recommendations:
        assert item.reason
        assert item.business_impact
        assert 0 <= item.risk_reduction <= 1
        assert item.implementation_cost
        assert item.implementation_effort
        assert item.estimated_time
        assert item.priority in Priority
        assert 0 <= item.confidence.score <= 1
        assert item.supporting_evidence
        assert item.category in RecommendationCategory
        assert item.audiences
        assert item.priority_score >= 0
    # critical/high expected for this high-risk sample
    assert report.counts["critical"] + report.counts["high"] >= 2
    assert Audience.EXECUTIVE.value in report.by_audience
    assert report.reasoning_path
    assert report.summary
