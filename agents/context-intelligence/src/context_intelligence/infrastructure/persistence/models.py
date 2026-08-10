"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="queued", index=True
    )
    source: Mapped[dict] = mapped_column(JSONB, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(256), nullable=False)
    webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_scans_tenant_idempotency"
        ),
        Index("ix_scans_tenant_created", "tenant_id", "created_at"),
    )


class ContextModelRecord(Base):
    __tablename__ = "context_models"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    scan_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scans.id"), nullable=False
    )
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    versions: Mapped[list["ModelVersion"]] = relationship(
        back_populates="model", cascade="all, delete-orphan"
    )


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    model_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("context_models.id"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    model: Mapped[ContextModelRecord] = relationship(back_populates="versions")

    __table_args__ = (UniqueConstraint("model_id", "version", name="uq_model_version"),)


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    scan_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scans.id"), nullable=False, index=True
    )
    model_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    scan_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("scans.id"), nullable=False, index=True
    )
    evidence_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    detector_id: Mapped[str] = mapped_column(String(128), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    excerpt_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(256), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="read")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
