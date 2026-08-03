"""Agent routing + version routing + health."""

from __future__ import annotations
from gie_contracts.orchestrator import AgentEndpoint, AgentId
from orchestrator.settings import Settings

def agent_base_urls(settings: Settings) -> dict[AgentId, str]:
    return {
        AgentId.CONTEXT: settings.context_url,
        AgentId.KNOWLEDGE: settings.knowledge_url,
        AgentId.POLICY: settings.policy_url,
        AgentId.RISK: settings.risk_url,
        AgentId.COMPLIANCE: settings.compliance_url,
        AgentId.RECOMMENDATION: settings.recommendation_url,
        AgentId.GENERATOR: settings.generator_url,
        AgentId.EXPLAINABILITY: settings.explainability_url,
        AgentId.VALIDATION: settings.validation_url,
        AgentId.LEARNING: settings.learning_url,
        AgentId.INTEGRATION: settings.integration_url,
    }

def resolve_version(agent_id: AgentId, agent_versions: dict[str, str], step_version: str | None = None) -> str:
    if step_version:
        return step_version
    return agent_versions.get(agent_id.value) or agent_versions.get(agent_id.value.replace("_", "-")) or "1.0.0"

def default_health(settings: Settings) -> list[AgentEndpoint]:
    urls = agent_base_urls(settings)
    out: list[AgentEndpoint] = []
    for agent_id, url in urls.items():
        # core pipeline agents marked healthy by default in simulate mode
        core = agent_id in {
            AgentId.CONTEXT, AgentId.KNOWLEDGE, AgentId.RISK, AgentId.COMPLIANCE,
            AgentId.POLICY, AgentId.RECOMMENDATION, AgentId.GENERATOR,
            AgentId.VALIDATION, AgentId.EXPLAINABILITY,
        }
        out.append(AgentEndpoint(agent_id=agent_id, base_url=url, version="1.0.0", healthy=core or settings.simulate_agents, latency_ms_p95=40.0 if core else 80.0))
    return out
