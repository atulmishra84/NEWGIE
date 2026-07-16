"""Integration test — scan fixture project."""

from __future__ import annotations

from pathlib import Path

from context_intelligence.application.scan_service import scan_folder


def test_folder_scan_detects_frameworks_and_mcp(sample_project_path: Path):
    model = scan_folder(sample_project_path, tenant_id="test-tenant")
    framework_names = {f.name for f in model.ai.frameworks}
    assert "langgraph" in framework_names
    sdk_names = {s.name for s in model.ai.sdks}
    assert "openai" in sdk_names
    mcp_names = {m.name for m in model.interfaces.mcp_servers}
    assert "filesystem" in mcp_names
    assert "github" in mcp_names


def test_folder_scan_detects_prompts(sample_project_path: Path):
    model = scan_folder(sample_project_path, tenant_id="test-tenant")
    prompt_names = {p.name for p in model.ai.prompts}
    assert "system" in prompt_names


def test_folder_scan_fingerprints_secrets_not_raw(sample_project_path: Path):
    model = scan_folder(sample_project_path, tenant_id="test-tenant")
    assert len(model.data.secret_findings) >= 1
    for finding in model.data.secret_findings:
        assert finding.fingerprint.startswith("sha256:")
        assert "sk-test" not in finding.fingerprint
    payload = model.model_dump_json()
    assert "sk-test-fake-key" not in payload


def test_folder_scan_sets_project_name(sample_project_path: Path):
    model = scan_folder(sample_project_path, tenant_id="test-tenant")
    assert model.identity.project_name == "sample_ai_project"
