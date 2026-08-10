from risk_intelligence.domain.engine import calculate_risk


def test_calculates_all_categories(sample_bundle):
    report = calculate_risk(sample_bundle)
    assert len(report.factors) == 16
    assert 0 <= report.overall_ai_risk_score <= 1
    assert 0 <= report.trust_score <= 1
    assert report.reasoning_path
    assert report.heatmap
    assert report.risk_graph["nodes"]
    assert "LLM01" in report.mappings_summary.get("owasp_llm", [])
    assert report.remediations
    for f in report.factors:
        assert f.explanation
        assert f.confidence.score >= 0
