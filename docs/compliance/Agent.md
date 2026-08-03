# Compliance Intelligence Agent

## Mission

Automatically determine which regulations, frameworks, and enterprise policies apply to an AI application; detect gaps; recommend controls; produce evidence and audit artifacts; maintain mapping with policy versioning and regulatory update tracking; compute a compliance score.

## Schema

`gie.compliance.v1`

## Supported frameworks

HIPAA, GDPR, PCI DSS, SOC2, ISO27001, NIST AI RMF, NIST CSF, EU AI Act, FDA, RBI, MAS, DORA, CCPA, Internal Corporate Policies.

## Inputs

Context Model, Risk Report, Knowledge hits, Identity metadata, Business context, declared frameworks, implemented controls, evidence items, internal policies.

## Outputs

| Artifact | Description |
|----------|-------------|
| Compliance Matrix | Framework × control status grid |
| Gap Analysis | Missing/partial controls with severity + remediations |
| Evidence Report | Collected evidence items per control |
| Audit Package | Bundle metadata for auditors |
| Control Mapping | Framework → control_id lists |
| Compliance Dashboard | Aggregated report payload |
| Compliance Score | 0–1 score (implemented + 0.5×partial) |

## APIs

| Method | Path |
|--------|------|
| POST | `/compliance/analyze` and `/v1/compliance/analyze` |
| POST | `/compliance/validate` and `/v1/compliance/validate` |
| GET | `/compliance/report` and `/v1/compliance/report` |
| GET | `/compliance/evidence` and `/v1/compliance/evidence` |
| GET | `/frameworks` and `/v1/frameworks` |

## Policy versioning

Reports stamp `policy_version` from the request or catalog (`2026.07.1`). Catalog entries include `last_update` for regulatory tracking.
