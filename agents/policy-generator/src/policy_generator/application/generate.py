from __future__ import annotations
import time
from gie_contracts.policy_generator import PolicyPackageGenerateRequest, PolicyPackage
from gie_contracts.policy_generator_events import PolicyPackageGenerationCompleted
from gie_observability.logging import get_logger
from policy_generator.domain.engine import generate_policy_package
from policy_generator.domain.ports import CacheStore, EventPublisher, PolicyPackageRepository
from policy_generator.settings import Settings
from policy_generator.version import AGENT_VERSION

logger = get_logger(__name__)

class GeneratePolicyHandler:
    def __init__(self, *, packages: PolicyPackageRepository, cache: CacheStore, events: EventPublisher, settings: Settings):
        self._packages = packages
        self._cache = cache
        self._events = events
        self._settings = settings

    async def handle(self, request: PolicyPackageGenerateRequest, *, actor: str, correlation_id: str) -> PolicyPackage:
        started = time.perf_counter()
        prior = await self._packages.latest_for_agent(request.bundle.tenant_id, request.bundle.agent_id)
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
            await self._events.publish(self._settings.kafka_topic_events, evt.model_dump(mode="json"), key=package.agent_id)
        logger.info("policy_package_generated", agent_id=package.agent_id, count=len(package.policies), actor=actor)
        return package
