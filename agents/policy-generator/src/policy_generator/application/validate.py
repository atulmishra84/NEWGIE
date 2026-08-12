from __future__ import annotations
import json
from gie_contracts.policy_generator import (
    PolicyPackageValidateRequest,
    ValidationResult,
    ValidationStatus,
    utcnow,
)
from gie_contracts.policy_generator_events import PolicyPackageValidationCompleted
from gie_observability.logging import get_logger
from policy_generator.application.errors import NotFoundError, PolicyGenError
from policy_generator.domain.engine import validate_content
from policy_generator.domain.ports import EventPublisher, PolicyPackageRepository
from policy_generator.settings import Settings
from policy_generator.version import AGENT_VERSION

logger = get_logger(__name__)


class ValidatePolicyHandler:
    def __init__(
        self,
        *,
        packages: PolicyPackageRepository,
        events: EventPublisher,
        settings: Settings,
    ):
        self._packages = packages
        self._events = events
        self._settings = settings

    async def handle(
        self, request: PolicyPackageValidateRequest, *, actor: str, correlation_id: str
    ) -> dict:
        package_id = request.package_id
        if request.package_id:
            pkg = await self._packages.get(request.package_id)
            if not pkg:
                raise NotFoundError(f"Policy package {request.package_id} not found")
            errors: list[str] = []
            warnings: list[str] = []
            checks: list[dict] = []
            for p in pkg.policies:
                vr = validate_content(p.content, p.format)
                p.validation = vr
                errors.extend(vr.errors)
                warnings.extend(vr.warnings)
                checks.append({"filename": p.filename, "status": vr.status.value})
            status = (
                ValidationStatus.INVALID
                if errors
                else (ValidationStatus.WARNING if warnings else ValidationStatus.VALID)
            )
            result = ValidationResult(
                status=status,
                checked_at=utcnow(),
                errors=errors,
                warnings=warnings,
                checks=checks,
            )
            pkg.validation = result
            await self._packages.save(pkg)
        elif request.content:
            result = validate_content(request.content, request.format)
        elif request.policy:
            result = validate_content(json.dumps(request.policy), request.format)
        else:
            raise PolicyGenError(
                "invalid_request", "Provide package_id, content, or policy"
            )
        evt = PolicyPackageValidationCompleted(
            tenant_id="default",
            correlation_id=correlation_id,
            producer_version=AGENT_VERSION,
            package_id=package_id,
            status=result.status.value,
            error_count=len(result.errors),
        )
        await self._events.publish(
            self._settings.kafka_topic_events,
            evt.model_dump(mode="json"),
            key=str(package_id or "adhoc"),
        )
        logger.info("policy_validated", status=result.status.value, actor=actor)
        return {
            "validation": result,
            "package_id": str(package_id) if package_id else None,
        }
