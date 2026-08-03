from __future__ import annotations
from gie_contracts.risk import RiskCalculateRequest, RiskRecalculateRequest
from risk_intelligence.application.calculate_risk import CalculateRiskHandler
from risk_intelligence.application.errors import NotFoundError
from risk_intelligence.domain.ports import CacheStore, RiskReportRepository

class RecalculateRiskHandler:
    def __init__(self, *, reports: RiskReportRepository, calculate: CalculateRiskHandler, cache: CacheStore):
        self._reports = reports
        self._calculate = calculate
        self._cache = cache

    async def handle(self, request: RiskRecalculateRequest, *, actor: str, correlation_id: str):
        if request.bundle is None:
            cached = await self._cache.get_json(f"risk:bundle:{request.tenant_id}:{request.agent_id}")
            if not cached:
                raise NotFoundError(
                    f"No cached inputs for agent {request.agent_id}; provide bundle for recalculation"
                )
            from gie_contracts.risk import RiskInputBundle
            bundle = RiskInputBundle.model_validate(cached)
        else:
            bundle = request.bundle
            bundle.tenant_id = request.tenant_id
            bundle.agent_id = request.agent_id
        if request.org_risk_model:
            bundle.org_risk_model = request.org_risk_model
        return await self._calculate.handle(
            RiskCalculateRequest(bundle=bundle, persist=True),
            actor=actor,
            correlation_id=correlation_id,
        )
