"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from context_intelligence.adapters.rest.app import app
from context_intelligence.settings import get_settings

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_ai_project"
OPENAPI_SPEC = Path(__file__).resolve().parents[3] / "docs" / "api" / "openapi.yaml"


def make_jwt(*, tenant_id: str = "test-tenant", roles: list[str] | None = None, subject: str = "test-user") -> str:
    settings = get_settings()
    payload = {
        "sub": subject,
        "tenant_id": tenant_id,
        "roles": roles or ["read"],
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.fixture
def sample_project_path() -> Path:
    assert SAMPLE_PROJECT.is_dir(), f"missing fixture project at {SAMPLE_PROJECT}"
    return SAMPLE_PROJECT


@pytest.fixture
def openapi_spec_path() -> Path:
    assert OPENAPI_SPEC.is_file(), f"missing OpenAPI spec at {OPENAPI_SPEC}"
    return OPENAPI_SPEC


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def read_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_jwt(roles=['read'])}"}


@pytest.fixture
def write_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_jwt(roles=['write'])}"}


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_jwt(roles=['admin'])}"}
