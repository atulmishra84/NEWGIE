# Policy Generator Agent

## Mission

Convert recommendations into deployment-ready policies across frameworks, platforms, and infrastructure.

## Schema

`gie.policygen.v1`

## Generated formats

OpenAI Guardrails · Azure AI Foundry · LangGraph · CrewAI · AutoGen · Semantic Kernel · NVIDIA NeMo · OPA/Rego · YAML · JSON · Terraform · Kubernetes · Admission Controllers · API Gateway · Prompt · Identity · Runtime · DLP

## Per-policy fields

Metadata · Version · Source · Compliance Mapping · Risk Mapping · Validation · Rollback

## Named artifacts

- `guardrails.yaml`
- `guardrails.json`
- `opa.rego`
- `azure-foundry-policy.json`
- `openai-policy.json`

## APIs

| Method | Path |
|--------|------|
| POST | `/policy/generate` and `/v1/policy/generate` |
| POST | `/policy/validate` and `/v1/policy/validate` |
| GET | `/policy/templates` and `/v1/policy/templates` |
| GET | `/policy/{id}` and `/v1/policy/{id}` |

Distinct from Policy Intelligence (`gie.policy.v1` on :8082), which selects guardrails. This agent materializes full deployment packages from recommendations on :8086.
