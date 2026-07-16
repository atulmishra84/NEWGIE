"""Execute scan command — orchestrates the detection pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from gie_contracts.events import ContextScanCompleted, ContextScanFailed, ContextScanStarted
from gie_observability import ACTIVE_SCANS, SCAN_DURATION, SCAN_REQUESTS, get_logger, traced
from gie_observability.context import new_request_context

from context_intelligence.application.errors import ScanNotFoundError
from context_intelligence.application.pipeline import DetectionPipeline
from context_intelligence.config import Settings
from context_intelligence.domain.entities import ContextScan, ScanStatus
from context_intelligence.domain.ports import ContextRepository, EventPublisher, WorkspaceFactory

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ExecuteScanCommand:
    scan_id: UUID
    tenant_id: str
    correlation_id: str


@dataclass(frozen=True, slots=True)
class ExecuteScanResult:
    scan: ContextScan
    model_id: UUID
    model_version: int
    confidence: float
    duration_ms: int


class ExecuteScanHandler:
    def __init__(
        self,
        *,
        repository: ContextRepository,
        pipeline: DetectionPipeline,
        event_publisher: EventPublisher,
        workspace_factory: WorkspaceFactory,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._pipeline = pipeline
        self._event_publisher = event_publisher
        self._workspace_factory = workspace_factory
        self._settings = settings

    @traced("execute_scan")
    async def handle(self, command: ExecuteScanCommand) -> ExecuteScanResult:
        new_request_context(
            agent_version=self._settings.agent_version,
            correlation_id=command.correlation_id,
            tenant_id=command.tenant_id,
        )

        scan = await self._repository.get_scan(command.scan_id, command.tenant_id)
        if scan is None:
            raise ScanNotFoundError(command.scan_id, command.tenant_id)

        if scan.status == ScanStatus.CANCELLED:
            logger.info("scan_execution_skipped_cancelled", scan_id=str(scan.scan_id))
            raise ScanNotFoundError(command.scan_id, command.tenant_id)

        if scan.is_terminal:
            if scan.model_id is None:
                raise ScanNotFoundError(command.scan_id, command.tenant_id)
            return ExecuteScanResult(
                scan=scan,
                model_id=scan.model_id,
                model_version=scan.model_version or 1,
                confidence=0.0,
                duration_ms=scan.duration_ms or 0,
            )

        scan.mark_running()
        await self._repository.update_scan(scan)
        ACTIVE_SCANS.inc()

        await self._event_publisher.publish(
            ContextScanStarted(
                tenant_id=command.tenant_id,
                correlation_id=command.correlation_id,
                producer_version=self._settings.agent_version,
                scan_id=scan.scan_id,
            )
        )

        workspace = self._workspace_factory(scan.scan_id)
        source_type = scan.source.type.value

        try:
            model = await self._pipeline.run(scan, workspace)
            scan.mark_completed(
                model_id=model.model_id,
                model_version=model.version,
                source_digest=model.provenance.source_digest,
            )
            await self._repository.update_scan(scan)

            duration_ms = scan.duration_ms or 0
            confidence = model.overall_confidence()

            await self._event_publisher.publish(
                ContextScanCompleted(
                    tenant_id=command.tenant_id,
                    correlation_id=command.correlation_id,
                    producer_version=self._settings.agent_version,
                    scan_id=scan.scan_id,
                    model_id=model.model_id,
                    model_version=model.version,
                    confidence=confidence,
                    duration_ms=duration_ms,
                )
            )

            SCAN_REQUESTS.labels(
                tenant_id=command.tenant_id,
                source_type=source_type,
                status=ScanStatus.COMPLETED.value,
            ).inc()
            if scan.started_at and scan.completed_at:
                SCAN_DURATION.labels(source_type=source_type).observe(
                    (scan.completed_at - scan.started_at).total_seconds()
                )

            logger.info(
                "scan_completed",
                scan_id=str(scan.scan_id),
                model_id=str(model.model_id),
                confidence=confidence,
                duration_ms=duration_ms,
            )
            return ExecuteScanResult(
                scan=scan,
                model_id=model.model_id,
                model_version=model.version,
                confidence=confidence,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            error_code = type(exc).__name__
            scan.mark_failed(error_code=error_code, error_message=str(exc), retryable=True)
            await self._repository.update_scan(scan)

            await self._event_publisher.publish(
                ContextScanFailed(
                    tenant_id=command.tenant_id,
                    correlation_id=command.correlation_id,
                    producer_version=self._settings.agent_version,
                    scan_id=scan.scan_id,
                    error_code=error_code,
                    error_message=str(exc),
                    retryable=True,
                )
            )
            SCAN_REQUESTS.labels(
                tenant_id=command.tenant_id,
                source_type=source_type,
                status=ScanStatus.FAILED.value,
            ).inc()
            logger.exception("scan_failed", scan_id=str(scan.scan_id), error_code=error_code)
            raise
        finally:
            ACTIVE_SCANS.dec()
            await workspace.cleanup()
