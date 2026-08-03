# Explainability Architecture

```mermaid
flowchart LR
  Inputs[Risk Compliance Recs Policies Knowledge] --> Engine[Explanation Engine]
  Engine --> Views[Executive Developer Security Compliance Auditor]
  Engine --> Arts[Markdown HTML PDF JSON]
  Engine --> Path[Reasoning Path]
  Path --> Mermaid[Mermaid Flowchart]
  Mermaid --> Figma[FigJam generate_diagram payload]
```
