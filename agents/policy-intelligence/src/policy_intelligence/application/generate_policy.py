"""Generate policy decisions from input bundles."""

from __future__ import annotations

import hashlib
import json
import time

from gie_contracts.policy import PolicyDecision, PolicyGenerateRequest
from gie_contracts.policy_events import PolicyGenerationCompleted
from gie_observability.logging import get_logger

from policy_intelligence.domain.engine import determine_guardrails
from policy_intelligence.domain.generators import generate_artifacts
from policy_intelligence.domain.ports import (
    CacheStore,
    DecisionRepository,
    EventPublisher,
)
from gie_llm import BedrockLLMClient
from policy_intelligence.settings import Settings
from policy_intelligence.version import AGENT_VERSION

logger = get_logger(__name__)


class GeneratePolicyHandler:
    def __init__(
        self,
        *,
        decisions: DecisionRepository,
        cache: CacheStore,
        events: EventPublisher,
        settings: Settings,
    ) -> None:
        self._decisions = decisions
        self._cache = cache
        self._events = events
        self._settings = settings
        self._llm = (
            BedrockLLMClient(
                region=settings.aws_region,
                model_id=settings.bedrock_model_id,
                max_tokens=settings.bedrock_max_tokens,
                temperature=settings.bedrock_temperature,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                aws_session_token=settings.aws_session_token,
            )
            if settings.bedrock_enabled
            else None
        )

    async def handle(
        self, request: PolicyGenerateRequest, *, actor: str, correlation_id: str
    ) -> PolicyDecision:
        started = time.perf_counter()
        bundle = request.bundle
        digest = hashlib.sha256(
            json.dumps(bundle.model_dump(mode="json"), sort_keys=True).encode()
        ).hexdigest()
        cache_key = f"pol:dec:{bundle.tenant_id}:{digest}"
        if not request.dry_run:
            cached = await self._cache.get_json(cache_key)
            if cached:
                return PolicyDecision.model_validate(cached)

        recs, reasoning, confidence = determine_guardrails(bundle)
        artifacts = generate_artifacts(recs, bundle)
        decision = PolicyDecision(
            tenant_id=bundle.tenant_id,
            agent_version=AGENT_VERSION,
            recommendations=recs,
            artifacts=artifacts,
            reasoning_path=reasoning,
            confidence=confidence,
            summary=self._summary(recs, artifacts),
            input_digest=digest,
        )
        if not request.dry_run:
            await self._decisions.save(decision)
            await self._cache.set_json(
                cache_key,
                decision.model_dump(mode="json"),
                self._settings.cache_ttl_seconds,
            )
            evt = PolicyGenerationCompleted(
                tenant_id=bundle.tenant_id,
                correlation_id=correlation_id,
                producer_version=AGENT_VERSION,
                decision_id=decision.decision_id,
                artifact_count=len(artifacts),
                recommendation_count=len(recs),
                confidence=confidence.score,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            await self._events.publish(
                self._settings.kafka_topic_events,
                evt.model_dump(mode="json"),
                key=str(decision.decision_id),
            )
        logger.info(
            "policy_generated",
            decision_id=str(decision.decision_id),
            recommendations=len(recs),
            artifacts=len(artifacts),
            actor=actor,
        )
        return decision

    def _summary(self, recs, artifacts) -> str:
        p0 = sum(1 for r in recs if r.priority.value == "P0")
        return f"{len(recs)} guardrails apply ({p0} P0); {len(artifacts)} deployment artifacts generated."
