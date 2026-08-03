# Orchestrator Architecture

## Sequence — unified analyze

```mermaid
sequenceDiagram
  participant Client
  participant Orch as Orchestrator
  participant Ctx as Context
  participant Know as Knowledge
  participant Risk as Risk
  participant Comp as Compliance
  participant Pol as Policy
  participant Rec as Recommendation
  participant Gen as Generator
  participant Val as Validation
  participant Exp as Explainability

  Client->>Orch: POST /analyze
  Orch->>Ctx: invoke
  Ctx-->>Orch: context model
  Orch->>Know: invoke
  Know-->>Orch: knowledge hits
  par Post-knowledge
    Orch->>Risk: invoke
    Orch->>Comp: invoke
  end
  Risk-->>Orch: risk report
  Comp-->>Orch: compliance report
  Orch->>Pol: invoke
  Pol-->>Orch: policies
  Orch->>Rec: invoke
  Rec-->>Orch: recommendations
  Orch->>Gen: invoke
  Gen-->>Orch: policy package
  Orch->>Val: invoke
  Val-->>Orch: validation
  Orch->>Exp: invoke
  Exp-->>Orch: explanation
  Orch-->>Client: UnifiedAnalysisResult
```

## State machine

```mermaid
stateDiagram-v2
  [*] --> Pending
  Pending --> Running: start
  Running --> WaitingApproval: approval gate
  WaitingApproval --> Running: approved
  WaitingApproval --> Cancelled: rejected
  Running --> Completed: all steps ok
  Running --> Partial: optional failures
  Running --> Failed: hard failure
  Running --> TimedOut: deadline
  Completed --> [*]
  Partial --> [*]
  Failed --> [*]
  TimedOut --> [*]
  Cancelled --> [*]
```

## Execution graph (default parallel)

```mermaid
flowchart TD
  context --> knowledge
  knowledge --> risk
  knowledge --> compliance
  risk --> policy
  compliance --> policy
  policy --> recommendation
  recommendation --> generator
  generator --> validation
  validation --> explainability
```

## Retry strategy

| Layer | Strategy |
|-------|----------|
| Step | Exponential backoff (`base * 2^attempt`), default 2 retries |
| Retryable errors | timeouts, unavailable, 5xx |
| Circuit (downstream) | Integration agent circuit breakers for external systems |
| Global | Optional `timeout_ms` on analyze request |

## Performance optimizations (enterprise)

1. **Parallel waves** — Risk ∥ Compliance after Knowledge
2. **Step result caching** — SHA-256 keyed by tenant + step + input fingerprint
3. **Async mode** — return quickly; poll `/execution/{id}`
4. **Batch concurrency limit** — protect downstream agents
5. **Version routing** — pin agent versions per request
6. **Distributed tracing** — span per step; query `/trace/{id}`
7. **Event publishing** — started / step / completed / approval for bus consumers
8. **Simulate mode** — local/CI without requiring all agents up
