"""Application-level errors."""

from __future__ import annotations

from uuid import UUID


class ApplicationError(Exception):
    """Base application error with stable code."""


class ScanNotFoundError(ApplicationError):
    def __init__(self, scan_id: UUID, tenant_id: str) -> None:
        self.scan_id = scan_id
        self.tenant_id = tenant_id
        super().__init__(f"Scan {scan_id} not found for tenant {tenant_id}")


class ModelNotFoundError(ApplicationError):
    def __init__(self, model_id: UUID, tenant_id: str) -> None:
        self.model_id = model_id
        self.tenant_id = tenant_id
        super().__init__(f"Context model {model_id} not found for tenant {tenant_id}")


class ScanNotCancellableError(ApplicationError):
    def __init__(self, scan_id: UUID, status: str) -> None:
        self.scan_id = scan_id
        self.status = status
        super().__init__(f"Scan {scan_id} cannot be cancelled in status {status}")
