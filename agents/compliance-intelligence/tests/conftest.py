import os
from pathlib import Path
import pytest
import pytest_asyncio
from gie_contracts.compliance import ComplianceInputBundle, FrameworkId
from compliance_intelligence.infrastructure.bootstrap import build_container
from compliance_intelligence.settings import Settings

os.environ.setdefault(
    "GIE_COMPLIANCE_CATALOG_PATH",
    str(
        Path(__file__).resolve().parents[1] / "data" / "frameworks" / "catalog_v1.json"
    ),
)


@pytest.fixture
def settings():
    return Settings(gie_env="test", require_auth=False)


@pytest_asyncio.fixture
async def container(settings):
    return await build_container(memory=True, settings=settings)


@pytest.fixture
def sample_bundle():
    return ComplianceInputBundle(
        tenant_id="acme",
        application_id="app-health-bot",
        context_model={
            "ai": {
                "frameworks": [{"name": "langgraph"}, {"name": "openai"}],
                "models": [{"name": "gpt-4o"}],
            },
            "data": {"pii_types": ["phi", "ssn"], "secret_findings": []},
            "interfaces": {"tools": [{"name": "ehr_lookup"}], "mcp_servers": []},
            "deployment": {"region": "us-east-1", "exposure": "private"},
        },
        risk_report={
            "overall_ai_risk_score": 0.62,
            "factors": [{"category": "privacy", "score": 0.7}],
        },
        knowledge={"hits": [{"node_id": "hipaa"}, {"node_id": "gdpr"}]},
        identity={"providers": ["okta"], "mfa": True},
        business={
            "industry": "healthcare",
            "criticality": "critical",
            "regions": ["US", "EU"],
        },
        declared_frameworks=[FrameworkId.HIPAA, FrameworkId.GDPR, FrameworkId.SOC2],
        implemented_controls=["hipaa-access"],
        evidence=[],
        internal_policies=[
            {"id": "pol-shadow-ai", "title": "No unsanctioned AI tools"}
        ],
    )
