from gie_contracts.explainability import ReasoningStep
from explainability_intelligence.domain.diagram import build_mermaid, figma_diagram_payload

def test_mermaid_has_no_reserved_end_id():
    steps = [ReasoningStep(step=1, agent="risk", action="score", detail="scored")]
    m = build_mermaid(steps)
    assert "flowchart LR" in m
    assert " end " not in f" {m} "
    payload = figma_diagram_payload(m)
    assert payload["diagramType"] == "flowchart"
