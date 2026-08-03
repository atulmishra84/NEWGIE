# Learning Intelligence Agent

## Mission

Continuously improve policy recommendations from production signals.

## Schema

`gie.learning.v1`

## Consumes

Runtime Telemetry · Security Incidents · False Positives · False Negatives · User Feedback · Threat Intelligence · Regulatory Updates · Policy Changes · Model Changes

## Capabilities

- Improve recommendations and confidence
- Detect policy drift, regulation changes, new attack techniques
- Recommend policy updates
- Generate learning reports
- Maintain recommendation/learning history
- Propose knowledge changes that **require human approval** before publishing

## APIs

| Method | Path |
|--------|------|
| POST | `/feedback` and `/v1/feedback` |
| POST | `/learn` and `/v1/learn` |
| GET | `/learning/history` and `/v1/learning/history` |
| GET | `/knowledge/changes` and `/v1/knowledge/changes` |
| POST | `/knowledge/approve` and `/v1/knowledge/approve` |
