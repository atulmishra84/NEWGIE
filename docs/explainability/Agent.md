# Explainability Intelligence Agent

## Mission

Explain every decision made by every GIE agent with multi-audience narratives and durable artifacts.

## Schema

`gie.explainability.v1`

## Recommendation explanation dimensions

Why · Evidence · Risk · Regulation · Business Impact · Confidence · Alternative Options · Expected Outcome · Supporting Knowledge · Policy Source

## Audience views

Executive · Developer · Security · Compliance · Auditor

## Artifacts

Markdown · HTML · PDF (text-printable) · JSON

## APIs

| Method | Path |
|--------|------|
| POST | `/explain` and `/v1/explain` |
| GET | `/explanation/{id}` and `/v1/explanation/{id}` |
| POST | `/reasoning/path` and `/v1/reasoning/path` |
| GET | `/figma-generate-diagram` and `/v1/figma-generate-diagram` |

`GET /figma-generate-diagram` returns a FigJam-ready `generate_diagram` payload (`mermaidSyntax` flowchart).
