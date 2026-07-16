"""Context scan aggregate and lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from gie_contracts.sources import ScanSource


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScanStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_VALID_TRANSITIONS: dict[ScanStatus, frozenset[ScanStatus]] = {
    ScanStatus.PENDING: frozenset({ScanStatus.RUNNING, ScanStatus.CANCELLED}),
    ScanStatus.RUNNING: frozenset(
        {ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED}
    ),
    ScanStatus.COMPLETED: frozenset(),
    ScanStatus.FAILED: frozenset(),
    ScanStatus.CANCELLED: frozenset(),
}


class InvalidScanTransitionError(Exception):
    """Raised when a scan status transition is not allowed."""


@dataclass
class ContextScan:
    """Aggregate root representing a context intelligence scan."""

    tenant_id: str
    source: ScanSource
    idempotency_key: str
    requested_by: str
    scan_id: UUID = field(default_factory=uuid4)
    status: ScanStatus = ScanStatus.PENDING
    created_at: datetime = field(default_factory=utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    model_id: UUID | None = None
    model_version: int | None = None
    source_digest: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = True
    webhook_url: str | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def can_transition_to(self, new_status: ScanStatus) -> bool:
        return new_status in _VALID_TRANSITIONS.get(self.status, frozenset())

    def _transition(self, new_status: ScanStatus) -> None:
        if not self.can_transition_to(new_status):
            raise InvalidScanTransitionError(
                f"Cannot transition scan {self.scan_id} from {self.status} to {new_status}"
            )
        self.status = new_status

    def mark_running(self) -> None:
        self._transition(ScanStatus.RUNNING)
        self.started_at = utcnow()

    def mark_completed(self, model_id: UUID, model_version: int, source_digest: str | None = None) -> None:
        self._transition(ScanStatus.COMPLETED)
        self.completed_at = utcnow()
        self.model_id = model_id
        self.model_version = model_version
        if source_digest:
            self.source_digest = source_digest
        self.error_code = None
        self.error_message = None

    def mark_failed(
        self,
        error_code: str,
        error_message: str,
        *,
        retryable: bool = True,
    ) -> None:
        self._transition(ScanStatus.FAILED)
        self.completed_at = utcnow()
        self.error_code = error_code
        self.error_message = error_message
        self.retryable = retryable

    def mark_cancelled(self) -> None:
        self._transition(ScanStatus.CANCELLED)
        self.completed_at = utcnow()

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            ScanStatus.COMPLETED,
            ScanStatus.FAILED,
            ScanStatus.CANCELLED,
        }

    @property
    def duration_ms(self) -> int | None:
        if self.started_at is None:
            return None
        end = self.completed_at or utcnow()
        return int((end - self.started_at).total_seconds() * 1000)

    @classmethod
    def create(
        cls,
        *,
        tenant_id: str,
        source: ScanSource,
        idempotency_key: str,
        requested_by: str,
        webhook_url: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ContextScan:
        return cls(
            tenant_id=tenant_id,
            source=source,
            idempotency_key=idempotency_key,
            requested_by=requested_by,
            webhook_url=webhook_url,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
