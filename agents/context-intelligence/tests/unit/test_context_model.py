"""Unit tests for ContextModel construction and validation."""

from __future__ import annotations

from uuid import uuid4

from gie_contracts.context_model import (
    CONTEXT_MODEL_SCHEMA,
    Confidence,
    ContextModel,
    ProvenanceSection,
)


def test_context_model_schema_version():
    model = ContextModel(
        provenance=ProvenanceSection(
            agent_version="1.0.0",
            scan_id=uuid4(),
            tenant_id="test",
            source_type="folder",
            confidence=Confidence(score=0.85),
        )
    )
    assert model.schema_version == CONTEXT_MODEL_SCHEMA
    assert model.overall_confidence() == 0.85


def test_context_model_default_sections():
    model = ContextModel(
        provenance=ProvenanceSection(
            agent_version="1.0.0",
            scan_id=uuid4(),
            tenant_id="test",
            source_type="folder",
        )
    )
    assert model.identity.languages == []
    assert model.ai.frameworks == []
    assert model.data.secret_findings == []
