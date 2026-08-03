# Recommendation Intelligence Agent

## Mission

Generate prioritized security recommendations for every AI application from Risk, Compliance, Context, Knowledge, Policies, Identity, and Runtime inputs.

## Schema

`gie.recommendation.v1`

## Priorities

Critical · High · Medium · Low

## Recommendation fields

Reason, Business Impact, Risk Reduction, Implementation Cost, Implementation Effort, Estimated Time, Priority, Confidence, Supporting Evidence, Dependencies, Category.

## Categories

Security · Privacy · Compliance · Identity · Runtime · Operations

## Audience packs

- Executive Recommendations
- Developer Recommendations
- Security Team Recommendations
- Platform Team Recommendations

## APIs

| Method | Path |
|--------|------|
| POST | `/recommendations` and `/v1/recommendations` |
| GET | `/recommendations/{agentId}` and `/v1/recommendations/{agentId}` |
| GET | `/recommendations/history` and `/v1/recommendations/history` |
| POST | `/recommendations/approve` and `/v1/recommendations/approve` |
