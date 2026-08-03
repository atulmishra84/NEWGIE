"""Execution graph: dependency resolution + parallel waves."""

from __future__ import annotations
from gie_contracts.orchestrator import AgentId, StepDefinition, WorkflowDefinition

def default_analyze_workflow(*, parallel_enabled: bool = True) -> WorkflowDefinition:
    """Canonical GIE pipeline with optional Risk||Compliance parallelization."""
    steps = [
        StepDefinition(step_id="context", agent_id=AgentId.CONTEXT, depends_on=[], timeout_ms=45_000),
        StepDefinition(step_id="knowledge", agent_id=AgentId.KNOWLEDGE, depends_on=["context"], timeout_ms=30_000),
        StepDefinition(
            step_id="risk",
            agent_id=AgentId.RISK,
            depends_on=["knowledge"],
            timeout_ms=30_000,
            parallel_group="post_knowledge" if parallel_enabled else None,
        ),
        StepDefinition(
            step_id="compliance",
            agent_id=AgentId.COMPLIANCE,
            depends_on=["knowledge"],
            timeout_ms=30_000,
            parallel_group="post_knowledge" if parallel_enabled else None,
        ),
        StepDefinition(step_id="policy", agent_id=AgentId.POLICY, depends_on=["risk", "compliance"], timeout_ms=30_000),
        StepDefinition(step_id="recommendation", agent_id=AgentId.RECOMMENDATION, depends_on=["policy"], timeout_ms=30_000),
        StepDefinition(step_id="generator", agent_id=AgentId.GENERATOR, depends_on=["recommendation"], timeout_ms=45_000),
        StepDefinition(step_id="validation", agent_id=AgentId.VALIDATION, depends_on=["generator"], timeout_ms=30_000),
        StepDefinition(step_id="explainability", agent_id=AgentId.EXPLAINABILITY, depends_on=["validation"], timeout_ms=30_000),
    ]
    return WorkflowDefinition(workflow_id="gie.analyze.default", name="GIE Unified Analysis", steps=steps, parallel_enabled=parallel_enabled)

def sequential_analyze_workflow() -> WorkflowDefinition:
    """Strict linear pipeline as specified in the mission (no parallel groups)."""
    order = [
        AgentId.CONTEXT,
        AgentId.KNOWLEDGE,
        AgentId.RISK,
        AgentId.COMPLIANCE,
        AgentId.POLICY,
        AgentId.RECOMMENDATION,
        AgentId.GENERATOR,
        AgentId.VALIDATION,
        AgentId.EXPLAINABILITY,
    ]
    steps: list[StepDefinition] = []
    prev: str | None = None
    for agent in order:
        sid = agent.value
        steps.append(StepDefinition(step_id=sid, agent_id=agent, depends_on=[prev] if prev else [], timeout_ms=30_000))
        prev = sid
    return WorkflowDefinition(workflow_id="gie.analyze.sequential", name="GIE Sequential Analysis", steps=steps, parallel_enabled=False)

def topological_waves(workflow: WorkflowDefinition) -> list[list[StepDefinition]]:
    """Return execution waves where each wave can run in parallel."""
    remaining = {s.step_id: s for s in workflow.steps}
    completed: set[str] = set()
    waves: list[list[StepDefinition]] = []
    while remaining:
        ready = [
            s
            for s in remaining.values()
            if all(d in completed for d in s.depends_on)
        ]
        if not ready:
            raise ValueError("Cycle or unmet dependencies in workflow graph")
        # If parallel disabled, force single-step waves in dependency-stable order
        if not workflow.parallel_enabled:
            # pick one with all deps met — prefer original order
            order_index = {s.step_id: i for i, s in enumerate(workflow.steps)}
            ready.sort(key=lambda s: order_index[s.step_id])
            ready = [ready[0]]
        waves.append(ready)
        for s in ready:
            completed.add(s.step_id)
            del remaining[s.step_id]
    return waves

def mermaid_execution_graph(workflow: WorkflowDefinition) -> str:
    lines = ["flowchart TD"]
    for s in workflow.steps:
        lines.append(f'  {s.step_id}["{s.agent_id.value}"]')
    for s in workflow.steps:
        for d in s.depends_on:
            lines.append(f"  {d} --> {s.step_id}")
    return "\n".join(lines)
