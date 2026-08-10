from gie_contracts.explainability import AudienceView, OutputFormat
from explainability_intelligence.domain.engine import explain_decision


def test_explains_all_views_and_formats(sample_bundle):
    report = explain_decision(sample_bundle)
    for aud in AudienceView:
        assert aud.value in report.views
    d = report.dimensions
    assert d.why
    assert d.evidence
    assert d.risk
    assert d.regulation
    assert d.business_impact
    assert d.confidence.score > 0
    assert d.alternative_options
    assert d.expected_outcome
    assert d.supporting_knowledge
    assert d.policy_source
    formats = {a.format for a in report.artifacts}
    assert OutputFormat.MARKDOWN in formats
    assert OutputFormat.HTML in formats
    assert OutputFormat.PDF in formats
    assert OutputFormat.JSON in formats
    assert "flowchart" in report.mermaid_diagram
    assert report.figma_diagram.get("tool") == "generate_diagram"
    assert report.figma_diagram.get("mermaidSyntax")
