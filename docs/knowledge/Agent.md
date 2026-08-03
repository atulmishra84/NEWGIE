# Knowledge Intelligence Agent

## Mission

The Knowledge Intelligence Agent is the **brain** of the Guardrails Intelligence Engine (GIE). It maintains a versioned, evidence-backed knowledge graph and provides explainable semantic retrieval for downstream agents (Risk, Policy, Compliance, Generator, Explainability).

## Schema

`gie.knowledge.v1`

## Owned capability

Exactly one capability: **curate, version, embed, query, and explain enterprise AI security/compliance knowledge**.

It does **not** scan applications (Context Agent) or recommend concrete policies (Policy Agent). It supplies authoritative knowledge those agents consume.

## Knowledge domains

| Domain | Contents |
|--------|----------|
| OWASP LLM Top 10 | LLM threats LLM01–LLM10 |
| MITRE ATLAS | Adversarial ML techniques |
| NIST AI RMF | Govern / Map / Measure / Manage |
| HIPAA, PCI DSS, SOC2, ISO27001, GDPR, EU AI Act | Controls |
| Financial / Healthcare regulations | Sector overlays |
| Identity security | Best practices & policies |
| Prompt injection / Jailbreak | Attack techniques |
| Guardrail templates | Reusable mitigations |
| Vendor capabilities | Platform safety features |
| Runtime restrictions | Runtime policy constraints |
| Policy mappings | Crosswalks between frameworks |

## Capabilities

- Semantic search (vector embeddings)
- Hybrid keyword + semantic + graph expansion
- Version control & diffs of the knowledge graph
- Evidence tracking on nodes/edges
- Explainable retrieval (`reasoning_path`, confidence, evidence)
- REST, MCP, CLI, SDK, Kafka events, webhooks

## Key APIs

- `POST /v1/knowledge/query` — explainable retrieval
- `POST /v1/knowledge/nodes` — upsert nodes/edges
- `GET /v1/knowledge/nodes/{id}` — get node + evidence
- `GET /v1/knowledge/versions` / `diff` — version control
- `POST /v1/knowledge/reindex` — rebuild embeddings

## MCP tools

`knowledge_query`, `knowledge_get_node`, `knowledge_upsert`, `knowledge_diff_versions`

## Security

OAuth2/JWT + API keys, RBAC (`knowledge:read|query|write|version|reindex|admin`), audit logging, least privilege.

## Observability

Every response includes `trace_id`, `request_id`, `correlation_id`, `execution_ms`, `confidence`, `reasoning_path`, `agent_version`.
