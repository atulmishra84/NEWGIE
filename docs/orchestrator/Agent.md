# Orchestrator Agent

## Mission

Coordinate every agent in the Guardrails Intelligence Engine through a unified analysis workflow.

## Schema

`gie.orchestrator.v1` · Port **8091**

## Unified APIs

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/analyze` | Sync / async / streaming unified analysis |
| POST | `/analyze/batch` | Batch analysis |
| POST | `/workflow` | Custom workflow execution |
| POST | `/approve` | Human approval gate |
| GET | `/status` | Orchestrator + agent health |
| GET | `/execution/{id}` | Execution state |
| GET | `/trace/{id}` | Distributed trace |
| GET | `/graph` | Execution graph (Mermaid + waves) |

## Execution modes

- **Synchronous** — block until completed (or waiting_approval)
- **Asynchronous** — return execution id immediately
- **Streaming** — SSE step events
- **Batch** — concurrent analyses with concurrency limit
- **Human approval** — pause at configured gates, resume via `/approve`

## Surfaces

REST · MCP · CLI (`gie-orchestrate`) · Python/TS SDKs
