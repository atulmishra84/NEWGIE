# Policy Intelligence Agent

## Mission

Consume Context, Risk, Compliance, Knowledge, Identity, and Business metadata to determine **which guardrails apply**, **why**, **priority**, **confidence**, **business impact**, and **implementation effort** — then emit deployment-ready policies.

## Schema

`gie.policy.v1`

## Inputs

| Input | Role |
|-------|------|
| Context | AI stack, tools, MCP, runtime |
| Risk | Scores & findings |
| Compliance | Framework obligations |
| Knowledge | Graph hits / control refs |
| Identity | IdP, auth schemes |
| Business | Criticality, industry, tier |

## Outputs

Artifacts for: OpenAI, Azure AI Foundry, LangGraph, CrewAI, AutoGen, OPA/Rego, NVIDIA NeMo, Microsoft Presidio

Formats: **YAML**, **JSON**, **Rego**, **vendor-native**

## APIs

- `POST /v1/policies/generate`
- `GET /v1/policies/decisions/{id}`
- `GET /v1/policies/decisions/{id}/explain`
- `GET /v1/policies/decisions/{id}/artifacts/{filename}`

## MCP

`policy_generate`, `policy_explain`, `policy_get_artifact`

## CLI

```bash
gie-policy generate ./bundle.json --out-dir ./policy-out
```
