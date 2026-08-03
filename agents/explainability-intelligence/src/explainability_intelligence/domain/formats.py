"""Render explanation artifacts as Markdown, HTML, PDF-text, and JSON."""

from __future__ import annotations

import html

from gie_contracts.explainability import ExplanationDimensions, ExplanationReport, OutputFormat, RenderedArtifact


def _dims_md(d: ExplanationDimensions) -> str:
    alts = "\n".join(f"- **{a.title}**: {a.description} ({a.tradeoffs})" for a in d.alternative_options) or "- None"
    evid = "\n".join(f"- {e}" for e in d.evidence) or "- None"
    know = "\n".join(f"- {k}" for k in d.supporting_knowledge) or "- None"
    return f"""### Why
{d.why}

### Evidence
{evid}

### Risk
{d.risk}

### Regulation
{d.regulation}

### Business Impact
{d.business_impact}

### Confidence
{d.confidence.score:.0%} — {d.confidence.rationale or ""}

### Alternative Options
{alts}

### Expected Outcome
{d.expected_outcome}

### Supporting Knowledge
{know}

### Policy Source
{d.policy_source}
"""


def render_markdown(report: ExplanationReport) -> str:
    parts = [
        f"# Explanation {report.explanation_id}",
        "",
        report.summary,
        "",
        "## Core Dimensions",
        _dims_md(report.dimensions),
        "",
        "## Audience Views",
    ]
    for view in report.views.values():
        parts.extend(
            [
                f"### {view.audience.value.title()} View — {view.title}",
                view.summary,
                "",
                view.narrative,
                "",
                _dims_md(view.dimensions),
            ]
        )
    parts.append("## Reasoning Path")
    for step in report.reasoning_path:
        parts.append(f"{step.step}. **{step.agent}** / {step.action}: {step.detail}")
    if report.mermaid_diagram:
        parts.extend(["", "## Decision Diagram", "```mermaid", report.mermaid_diagram, "```"])
    return "\n".join(parts)


def render_html(report: ExplanationReport) -> str:
    mdish = render_markdown(report)
    body = html.escape(mdish).replace("\n", "<br/>\n")
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>Explanation {report.explanation_id}</title>
<style>body{{font-family:Georgia,serif;max-width:900px;margin:2rem auto;line-height:1.5;color:#1a1a1a}} h1,h2,h3{{color:#0b3d5c}}</style>
</head><body><pre style="white-space:pre-wrap;font-family:inherit">{body}</pre></body></html>
"""


def render_pdf_text(report: ExplanationReport) -> str:
    """Auditor-ready printable body. Binary PDF can replace this later."""
    header = f"%GIE-EXPLAIN-PDF-1.0\n% explanation_id={report.explanation_id}\n"
    return header + render_markdown(report)


def render_json(report: ExplanationReport) -> str:
    return report.model_dump_json(indent=2)


def build_artifacts(report: ExplanationReport, formats: list[OutputFormat] | None = None) -> list[RenderedArtifact]:
    wanted = formats or [OutputFormat.MARKDOWN, OutputFormat.HTML, OutputFormat.PDF, OutputFormat.JSON]
    out: list[RenderedArtifact] = []
    eid = str(report.explanation_id)[:8]
    for fmt in wanted:
        if fmt == OutputFormat.MARKDOWN:
            out.append(
                RenderedArtifact(
                    format=fmt,
                    filename=f"explanation-{eid}.md",
                    content_type="text/markdown",
                    content=render_markdown(report),
                )
            )
        elif fmt == OutputFormat.HTML:
            out.append(
                RenderedArtifact(
                    format=fmt,
                    filename=f"explanation-{eid}.html",
                    content_type="text/html",
                    content=render_html(report),
                )
            )
        elif fmt == OutputFormat.PDF:
            out.append(
                RenderedArtifact(
                    format=fmt,
                    filename=f"explanation-{eid}.pdf.txt",
                    content_type="application/pdf",
                    content=render_pdf_text(report),
                )
            )
        elif fmt == OutputFormat.JSON:
            out.append(
                RenderedArtifact(
                    format=fmt,
                    filename=f"explanation-{eid}.json",
                    content_type="application/json",
                    content=render_json(report),
                )
            )
    return out
