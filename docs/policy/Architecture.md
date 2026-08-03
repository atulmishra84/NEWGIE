# Policy Intelligence Architecture

```mermaid
flowchart LR
  Inputs[Context Risk Compliance Knowledge Identity Business] --> Engine[Policy Engine]
  Engine --> Recs[Guardrail Recommendations]
  Recs --> Gen[Target Generators]
  Gen --> Arts[YAML JSON Rego VendorNative]
  Engine --> Store[(Decisions Cache Events)]
```

Hexagonal layers: adapters → application (generate/explain) → domain (catalog, engine, generators) → infrastructure.

Each recommendation includes why/priority/confidence/impact/effort plus knowledge/risk/compliance refs.
