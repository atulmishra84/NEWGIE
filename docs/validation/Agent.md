# Validation Intelligence Agent

## Mission

Validate every generated policy before deployment.

## Schema

`gie.validation.v1`

## Checks

Syntax · Schema · Compliance · Runtime Compatibility · Policy Conflicts · Duplicate Rules · Performance · Security · Framework Compatibility · Model Compatibility · Simulation

## Behaviors

- Simulate execution
- Detect invalid configurations
- Recommend corrections
- Generate validation reports
- Generate approval status (`approved` / `approved_with_warnings` / `rejected`)

## Outputs

Validation Report with verdict: **pass** · **warning** · **failed**

## APIs

| Method | Path |
|--------|------|
| POST | `/validate` and `/v1/validate` |
| POST | `/simulate` and `/v1/simulate` |
| GET | `/validation/{id}` and `/v1/validation/{id}` |
| GET | `/validation/report` and `/v1/validation/report` |
