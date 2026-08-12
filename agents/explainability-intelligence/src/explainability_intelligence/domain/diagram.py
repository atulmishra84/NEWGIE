"""Build FigJam-ready Mermaid reasoning diagrams."""

from __future__ import annotations

from typing import Any

from gie_contracts.explainability import ReasoningStep


def _safe_id(prefix: str, n: int) -> str:
    return f"{prefix}{n}"


def build_mermaid(
    steps: list[ReasoningStep], *, title: str = "Decision reasoning"
) -> str:
    lines = [
        "flowchart LR",
        f'  startNode(["{title}"])',
    ]
    prev = "startNode"
    for i, step in enumerate(steps, start=1):
        nid = _safe_id("step", i)
        label = f"{step.agent}: {step.action}"
        label = label.replace('"', "'")[:60]
        detail = step.detail.replace('"', "'")[:80]
        lines.append(f'  {nid}["{label}"]')
        lines.append(f"  {prev} --> {nid}")
        lines.append(f'  note{i}["{detail}"]')
        lines.append(f"  {nid} -.-> note{i}")
        prev = nid
    lines.append("  outcomeNode([Expected outcome])")
    lines.append(f"  {prev} ==> outcomeNode")
    return "\n".join(lines)


def figma_diagram_payload(
    mermaid: str, *, name: str = "GIE Decision Explanation"
) -> dict[str, Any]:
    """Payload consumable by Figma generate_diagram / FigJam workflows."""
    return {
        "tool": "generate_diagram",
        "name": name,
        "diagramType": "flowchart",
        "mermaidSyntax": mermaid,
        "userIntent": "Visualize multi-agent decision reasoning for auditors and executives",
        "instructions": "Open in FigJam via Figma generate_diagram using mermaidSyntax",
    }
