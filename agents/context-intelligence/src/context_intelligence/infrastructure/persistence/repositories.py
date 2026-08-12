"""SQLAlchemy ContextRepository and outbox writer."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from gie_contracts.context_model import ContextModel
from gie_contracts.events import EventEnvelope
from gie_contracts.sources import ScanSource
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from context_intelligence.domain.ports import ContextRepository, OutboxWriter
from context_intelligence.infrastructure.persistence.models import (
    ApiKey,
    AuditLog,
    ContextModelRecord,
    Evidence,
    Finding,
    ModelVersion,
    OutboxEvent,
    Scan,
)
from context_intelligence.settings import get_settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _scan_to_dict(row: Scan) -> dict[str, Any]:
    return {
        "scan_id": str(row.id),
        "tenant_id": row.tenant_id,
        "status": row.status,
        "source": row.source,
        "idempotency_key": row.idempotency_key,
        "requested_by": row.requested_by,
        "webhook_url": row.webhook_url,
        "correlation_id": row.correlation_id,
        "model_id": str(row.model_id) if row.model_id else None,
        "error_code": row.error_code,
        "error_message": row.error_message,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _hash_api_key(raw_key: str, pepper: str) -> str:
    return hmac.new(pepper.encode(), raw_key.encode(), hashlib.sha256).hexdigest()


class SqlAlchemyContextRepository(ContextRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_scan(
        self,
        *,
        scan_id: UUID,
        tenant_id: str,
        source: ScanSource,
        idempotency_key: str,
        requested_by: str,
        webhook_url: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        row = Scan(
            id=scan_id,
            tenant_id=tenant_id,
            status="queued",
            source=source.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            requested_by=requested_by,
            webhook_url=webhook_url,
            correlation_id=correlation_id,
        )
        self._session.add(row)
        await self._session.flush()
        return _scan_to_dict(row)

    async def get_scan(self, scan_id: UUID, tenant_id: str) -> dict[str, Any] | None:
        row = await self._session.get(Scan, scan_id)
        if not row or row.tenant_id != tenant_id:
            return None
        return _scan_to_dict(row)

    async def list_scans(
        self,
        tenant_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(Scan)
            .where(Scan.tenant_id == tenant_id)
            .order_by(Scan.created_at.desc())
        )
        if status:
            stmt = stmt.where(Scan.status == status)
        stmt = stmt.limit(limit).offset(offset)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_scan_to_dict(r) for r in rows]

    async def update_scan_status(
        self,
        scan_id: UUID,
        *,
        status: str,
        error_code: str | None = None,
        error_message: str | None = None,
        model_id: UUID | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        values: dict[str, Any] = {"status": status}
        if error_code is not None:
            values["error_code"] = error_code
        if error_message is not None:
            values["error_message"] = error_message
        if model_id is not None:
            values["model_id"] = model_id
        if started_at is not None:
            values["started_at"] = started_at
        if completed_at is not None:
            values["completed_at"] = completed_at
        await self._session.execute(
            update(Scan).where(Scan.id == scan_id).values(**values)
        )

    async def save_context_model(
        self,
        model: ContextModel,
        *,
        scan_id: UUID,
        tenant_id: str,
    ) -> int:
        record = await self._session.get(ContextModelRecord, model.model_id)
        if record is None:
            record = ContextModelRecord(
                id=model.model_id,
                tenant_id=tenant_id,
                scan_id=scan_id,
                current_version=1,
            )
            self._session.add(record)
            version_num = 1
        else:
            version_num = record.current_version + 1
            record.current_version = version_num
            record.updated_at = _utcnow()

        payload = model.model_dump(mode="json")
        model.version = version_num
        payload["version"] = version_num
        self._session.add(
            ModelVersion(
                model_id=model.model_id,
                version=version_num,
                schema_version=model.schema_version,
                payload=payload,
                confidence=model.overall_confidence(),
            )
        )
        await self._persist_findings(model, scan_id, tenant_id)
        await self._session.flush()
        return version_num

    async def _persist_findings(
        self, model: ContextModel, scan_id: UUID, tenant_id: str
    ) -> None:
        for secret in model.data.secret_findings:
            self._session.add(
                Finding(
                    tenant_id=tenant_id,
                    scan_id=scan_id,
                    model_id=model.model_id,
                    kind="secret",
                    severity=secret.severity.value,
                    title=f"Secret: {secret.kind}",
                    location=secret.location,
                    fingerprint=secret.fingerprint,
                    details=secret.model_dump(mode="json"),
                )
            )

    async def get_context_model(
        self,
        model_id: UUID,
        tenant_id: str,
        *,
        version: int | None = None,
    ) -> ContextModel | None:
        record = await self._session.get(ContextModelRecord, model_id)
        if not record or record.tenant_id != tenant_id:
            return None
        target_version = version or record.current_version
        stmt = select(ModelVersion).where(
            ModelVersion.model_id == model_id,
            ModelVersion.version == target_version,
        )
        mv = (await self._session.execute(stmt)).scalar_one_or_none()
        if not mv:
            return None
        return ContextModel.model_validate(mv.payload)

    async def list_model_versions(
        self, model_id: UUID, tenant_id: str
    ) -> list[dict[str, Any]]:
        record = await self._session.get(ContextModelRecord, model_id)
        if not record or record.tenant_id != tenant_id:
            return []
        stmt = (
            select(ModelVersion)
            .where(ModelVersion.model_id == model_id)
            .order_by(ModelVersion.version.desc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "version": r.version,
                "schema_version": r.schema_version,
                "confidence": r.confidence,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    async def diff_models(
        self,
        model_id: UUID,
        tenant_id: str,
        from_version: int,
        to_version: int,
    ) -> dict[str, Any]:
        left = await self.get_context_model(model_id, tenant_id, version=from_version)
        right = await self.get_context_model(model_id, tenant_id, version=to_version)
        if not left or not right:
            return {"error": "version_not_found"}
        left_json = left.model_dump(mode="json")
        right_json = right.model_dump(mode="json")
        changed_sections: list[str] = []
        for section in (
            "identity",
            "ai",
            "interfaces",
            "data",
            "security",
            "deployment",
            "graph",
        ):
            if left_json.get(section) != right_json.get(section):
                changed_sections.append(section)
        return {
            "model_id": str(model_id),
            "from_version": from_version,
            "to_version": to_version,
            "changed_sections": changed_sections,
            "confidence_delta": right.overall_confidence() - left.overall_confidence(),
        }

    async def list_findings(
        self,
        *,
        tenant_id: str,
        scan_id: UUID | None = None,
        model_id: UUID | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(Finding)
            .where(Finding.tenant_id == tenant_id)
            .order_by(Finding.created_at.desc())
        )
        if scan_id:
            stmt = stmt.where(Finding.scan_id == scan_id)
        if model_id:
            stmt = stmt.where(Finding.model_id == model_id)
        stmt = stmt.limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "finding_id": str(r.id),
                "kind": r.kind,
                "severity": r.severity,
                "title": r.title,
                "location": r.location,
                "fingerprint": r.fingerprint,
                "details": r.details,
                "scan_id": str(r.scan_id),
                "model_id": str(r.model_id) if r.model_id else None,
            }
            for r in rows
        ]

    async def save_evidence(
        self,
        *,
        scan_id: UUID,
        tenant_id: str,
        evidence_id: str,
        path: str | None,
        detector_id: str,
        excerpt: str | None,
        excerpt_hash: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._session.add(
            Evidence(
                tenant_id=tenant_id,
                scan_id=scan_id,
                evidence_id=evidence_id,
                path=path,
                detector_id=detector_id,
                excerpt=excerpt,
                excerpt_hash=excerpt_hash,
                metadata_json=metadata or {},
            )
        )

    async def write_audit_log(
        self,
        *,
        tenant_id: str,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self._session.add(
            AuditLog(
                tenant_id=tenant_id,
                actor=actor,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
            )
        )

    async def get_scan_by_idempotency_key(
        self,
        tenant_id: str,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        stmt = select(Scan).where(
            Scan.tenant_id == tenant_id,
            Scan.idempotency_key == idempotency_key,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _scan_to_dict(row) if row else None

    async def validate_api_key(self, raw_key: str) -> dict[str, Any] | None:
        settings = get_settings()
        key_hash = _hash_api_key(raw_key, settings.api_key_pepper)
        stmt = select(ApiKey).where(
            ApiKey.key_hash == key_hash, ApiKey.active.is_(True)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if not row:
            return None
        row.last_used_at = _utcnow()
        return {
            "tenant_id": row.tenant_id,
            "subject": f"apikey:{row.name}",
            "roles": _role_to_permissions(row.role),
            "role": row.role,
        }


def _role_to_permissions(role: str) -> set[str]:
    if role == "admin":
        return {"read", "write", "admin"}
    if role == "write":
        return {"read", "write"}
    return {"read"}


class SqlAlchemyOutboxWriter(OutboxWriter):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, event: EventEnvelope) -> UUID:
        event_id = event.event_id
        self._session.add(
            OutboxEvent(
                id=event_id,
                tenant_id=event.tenant_id,
                event_type=event.event_type,
                payload=event.model_dump(mode="json"),
                published=False,
            )
        )
        await self._session.flush()
        return event_id
