from __future__ import annotations
import time
from gie_contracts.policy_generator import PolicyPackageGenerateRequest, PolicyPackage
from gie_contracts.policy_generator_events import PolicyPackageGenerationCompleted
from gie_observability.logging import get_logger
from policy_generator.domain.engine import generate_policy_package
from policy_generator.domain.ports import (
    CacheStore,
    EventPublisher,
    PolicyPackageRepository,
)
from gie_llm import AnthropicLLMClient
from policy_generator.domain.llm_enhancer import enhance_policy_package
from policy_generator.settings import Settings
from policy_generator.version import AGENT_VERSION

logger = get_logger(__name__)


class GeneratePolicyHandler:
    def __init__(
        self,
        *,
        packages: PolicyPackageRepository,
        cache: CacheStore,
        events: EventPublisher,
        settings: Settings,
    ):
        self._packages = packages
        self._cache = cache
        self._events = events
        self._settings = settings
        self._llm = (
            AnthropicLLMClient(
                api_key=settings.anthropic_api_key,
                model_id=settings.anthropic_model_id,
                max_tokens=settings.anthropic_max_tokens,
            )
            if settings.anthropic_enabled
            else None
        )

    async def handle(
        self, request: PolicyPackageGenerateRequest, *, actor: str, correlation_id: str
    ) -> PolicyPackage:
        started = time.perf_counter()
        prior = await self._packages.latest_for_agent(
            request.bundle.tenant_id, request.bundle.agent_id
        )
        package = generate_policy_package(request.bundle, previous=prior)
        if request.persist:
            await self._packages.save(package)
            await self._cache.set_json(
                f"policygen:latest:{package.tenant_id}:{package.agent_id}",
                package.model_dump(mode="json"),
                self._settings.cache_ttl_seconds,
            )
            evt = PolicyPackageGenerationCompleted(
                tenant_id=package.tenant_id,
                correlation_id=correlation_id,
                producer_version=AGENT_VERSION,
                agent_id=package.agent_id,
                package_id=package.package_id,
                policy_count=len(package.policies),
                artifact_count=len(package.artifacts),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            await self._events.publish(
                self._settings.kafka_topic_events,
                evt.model_dump(mode="json"),
                key=package.agent_id,
            )
        if self._llm:
            package_dict = package.model_dump(mode="json")
            _enhanced = await enhance_policy_package(package_dict, client=self._llm)
            package = package.model_copy(
                update={
                    "llm_enhancement": {
                        "narrative": _enhanced.get("llm_narrative", ""),
                        "key_insights": _enhanced.get("llm_key_insights", []),
                        "recommendations": _enhanced.get("llm_recommendations", []),
                        "model": _enhanced.get("llm_model", ""),
                    }
                }
            )
        logger.info(
            "policy_package_generated",
            agent_id=package.agent_id,
            count=len(package.policies),
            actor=actor,
        )
        return package
