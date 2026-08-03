# Orchestrator Workflows

## Default pipeline (`gie.analyze.default`)

1. Context  
2. Knowledge  
3. Risk ∥ Compliance  
4. Policy  
5. Recommendation  
6. Generator  
7. Validation  
8. Explainability  

## Sequential pipeline (`gie.analyze.sequential`)

Strict linear order matching the mission statement (no parallel groups). Enable with `options.sequential=true`.

## Human approval

```json
{
  "require_human_approval": true,
  "approval_gates": ["validation"]
}
```

Execution status becomes `waiting_approval`. Resume:

```http
POST /approve
{"execution_id":"…","step_id":"validation","approved":true,"actor":"secops"}
```
