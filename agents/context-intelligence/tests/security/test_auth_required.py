"""Security tests — authentication required."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import make_jwt


def test_create_scan_requires_auth(api_client: TestClient):
    response = api_client.post(
        "/v1/scans",
        json={"source": {"type": "folder", "path": "/tmp"}},
    )
    assert response.status_code == 401


def test_get_scan_requires_auth(api_client: TestClient):
    response = api_client.get("/v1/scans/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 401


def test_health_is_public(api_client: TestClient):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_healthz_is_public(api_client: TestClient):
    response = api_client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_read_only_cannot_create_scan(api_client: TestClient, sample_project_path):
    token = make_jwt(roles=["read"])
    response = api_client.post(
        "/v1/scans",
        json={"source": {"type": "folder", "path": str(sample_project_path)}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_invalid_token_rejected(api_client: TestClient):
    response = api_client.get(
        "/v1/scans",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )
    assert response.status_code == 401
