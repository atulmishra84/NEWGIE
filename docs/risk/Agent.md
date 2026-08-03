# Risk Intelligence Agent

## Mission

Calculate the overall AI risk posture of an AI application with explainable scores, framework mappings, and remediations.

## Schema

`gie.risk.v1`

## Risk dimensions

Security, Privacy, Compliance, Identity, Prompt Injection, Jailbreak, Hallucination, Supply Chain, Model, Tool Abuse, Data Leakage, Shadow AI, Runtime, Autonomy, Business, Operational — plus **Overall AI Risk Score** and **Trust Score**.

## Inputs

Context Model, Knowledge Graph, Compliance Requirements, Identity Metadata, Runtime Configuration, AI Models, Prompt Analysis, Tool Permissions, Agent Capabilities, optional custom org risk model.

## Outputs

Risk Report, Risk Graph, Risk Timeline, Heatmap data, machine-readable JSON, Dashboard API, Risk History.

## APIs

| Method | Path |
|--------|------|
| POST | `/risk/calculate` and `/v1/risk/calculate` |
| POST | `/risk/recalculate` and `/v1/risk/recalculate` |
| GET | `/risk/{agentId}` and `/v1/risk/{agentId}` |
| GET | `/risk/history` and `/v1/risk/history` |
| GET | `/risk/remediation` and `/v1/risk/remediation` |
| GET | `/v1/risk/dashboard/{agentId}` |

## Mappings

Every factor maps to MITRE ATLAS, OWASP LLM Top 10, and NIST AI RMF where applicable.
