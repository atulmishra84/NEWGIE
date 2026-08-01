"""Agent registry with heartbeats for Full+GIE fleet."""

from __future__ import annotations

from datetime import datetime, timezone

from gie_contracts import (
    FULL_GIE_AGENT_IDS,
    FLEET_AGENT_META,
    AgentHeartbeat,
    AgentId,
)

# Platform agents may be external services; still registered for LT-5.
_EXTERNAL = {
    AgentId.CONTEXT_INTELLIGENCE,
    AgentId.RISK_ASSESSMENT,
    AgentId.POLICY_ENGINE,
}


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[AgentId, AgentHeartbeat] = {}
        self.bootstrap()

    def bootstrap(self) -> None:
        now = datetime.now(timezone.utc)
        for agent_id in FULL_GIE_AGENT_IDS:
            lane, name = FLEET_AGENT_META[agent_id]
            self._agents[agent_id] = AgentHeartbeat(
                agent_id=agent_id,
                lane=lane,
                display_name=name,
                healthy=True,
                last_seen=now,
                version="1.0.0",
            )

    def heartbeat(self, agent_id: AgentId, healthy: bool = True) -> AgentHeartbeat:
        lane, name = FLEET_AGENT_META[agent_id]
        hb = AgentHeartbeat(
            agent_id=agent_id,
            lane=lane,
            display_name=name,
            healthy=healthy,
            last_seen=datetime.now(timezone.utc),
        )
        self._agents[agent_id] = hb
        return hb

    def touch_all(self) -> None:
        for agent_id in list(self._agents):
            self.heartbeat(agent_id, healthy=True)

    def list_agents(self) -> list[AgentHeartbeat]:
        return list(self._agents.values())

    def healthy_count(self) -> int:
        return sum(1 for a in self._agents.values() if a.healthy)

    def expected_count(self) -> int:
        return len(FULL_GIE_AGENT_IDS)

    def mark_external(self, agent_id: AgentId, healthy: bool) -> None:
        if agent_id in _EXTERNAL:
            self.heartbeat(agent_id, healthy=healthy)


registry = AgentRegistry()
