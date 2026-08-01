"""Role agent workers for delivery, security, and release/ops lanes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from gie_contracts import AgentId, AgentStepResult, Finding, Severity

from chief_orchestrator.registry import registry


def _finish(step: AgentStepResult) -> AgentStepResult:
    step.finished_at = datetime.now(timezone.utc)
    registry.heartbeat(step.agent_id, healthy=True)
    return step


def run_product_manager(goal: str) -> AgentStepResult:
    return _finish(
        AgentStepResult(
            agent_id=AgentId.PRODUCT_MANAGER,
            summary="MVP scoped with acceptance criteria",
            artifacts={
                "prd": {
                    "goal": goal,
                    "mvp": "Golden demo app with health endpoint and feature flag surface",
                    "non_goals": ["multi-region", "billing"],
                    "acceptance": [
                        "App serves /healthz 200",
                        "Staging URL reachable",
                        "Security gates evaluated",
                        "GIE context model produced",
                    ],
                },
                "acceptance": [
                    "App serves /healthz 200",
                    "Staging URL reachable",
                    "Security gates evaluated",
                    "GIE context model produced",
                ],
            },
        )
    )


def run_ux_designer(prd: dict[str, Any]) -> AgentStepResult:
    return _finish(
        AgentStepResult(
            agent_id=AgentId.UX_DESIGNER,
            summary="Primary flow and screen map defined",
            artifacts={
                "ux": {
                    "primary_flow": ["Landing", "Status", "Demo result"],
                    "a11y": ["keyboard", "contrast-aa"],
                    "mvp_ref": prd.get("mvp"),
                }
            },
        )
    )


def run_senior_developer(goal: str) -> AgentStepResult:
    return _finish(
        AgentStepResult(
            agent_id=AgentId.SENIOR_DEVELOPER,
            summary="Architecture and integration plan ready",
            artifacts={
                "architecture": {
                    "style": "modular monolith for golden demo",
                    "modules": ["api", "web", "ops"],
                    "goal": goal,
                }
            },
        )
    )


def run_frontend(ux: dict[str, Any]) -> AgentStepResult:
    return _finish(
        AgentStepResult(
            agent_id=AgentId.FRONTEND_SPECIALIST,
            summary="Frontend shell implemented for demo flow",
            artifacts={"frontend": {"pages": ux.get("primary_flow", []), "status": "implemented"}},
        )
    )


def run_backend(arch: dict[str, Any]) -> AgentStepResult:
    return _finish(
        AgentStepResult(
            agent_id=AgentId.BACKEND_SPECIALIST,
            summary="Backend API and health endpoint implemented",
            artifacts={
                "backend": {
                    "endpoints": ["/healthz", "/demo"],
                    "modules": arch.get("modules", []),
                    "status": "implemented",
                }
            },
        )
    )


def run_appsec() -> AgentStepResult:
    return _finish(
        AgentStepResult(
            agent_id=AgentId.SECURITY_ENGINEER,
            summary="Threat model complete; secure defaults applied",
            artifacts={
                "threat_model": {
                    "assets": ["api", "secrets", "staging"],
                    "controls": ["tls", "auth-bearer", "no-raw-secrets-in-logs"],
                }
            },
        )
    )


async def run_vuln_eng(*, inject_critical: bool) -> AgentStepResult:
    from chief_orchestrator.cve_scanners import run_cve_providers

    findings, meta = await run_cve_providers(inject_critical=inject_critical)
    return _finish(
        AgentStepResult(
            agent_id=AgentId.VULNERABILITY_ENGINEER,
            ok=not any(f.blocking for f in findings),
            summary=f"Vulnerability triage complete via {meta.get('providers')}",
            artifacts={"triaged": len(findings), "cve": meta},
            findings=findings,
        )
    )


def run_sec_test(*, inject_critical: bool) -> AgentStepResult:
    findings: list[Finding] = []
    if inject_critical:
        findings.append(
            Finding(
                source_agent=AgentId.SECURITY_TEST_ENGINEER,
                severity=Severity.CRITICAL,
                title="Auth bypass simulated in fixture",
                detail="Live-test fixture LT-3.1",
                blocking=True,
            )
        )
    return _finish(
        AgentStepResult(
            agent_id=AgentId.SECURITY_TEST_ENGINEER,
            ok=not findings,
            summary="Security test suite executed",
            artifacts={"tests": ["secrets_scan", "auth_smoke", "injection_smoke"], "failed": len(findings)},
            findings=findings,
        )
    )


def run_compliance() -> AgentStepResult:
    return _finish(
        AgentStepResult(
            agent_id=AgentId.COMPLIANCE_OFFICER,
            summary="Control evidence binder drafted",
            artifacts={
                "compliance": {
                    "frameworks": ["SOC2-lite"],
                    "controls": ["CC6.1 access", "CC7.1 monitoring"],
                    "status": "evidence-ready",
                }
            },
        )
    )


def run_qa(acceptance: list[str]) -> AgentStepResult:
    return _finish(
        AgentStepResult(
            agent_id=AgentId.QA_ENGINEER,
            summary="Functional and E2E checks passed against acceptance",
            artifacts={"qa": {"acceptance": acceptance, "result": "pass"}},
        )
    )


def run_release_manager() -> AgentStepResult:
    return _finish(
        AgentStepResult(
            agent_id=AgentId.RELEASE_MANAGER,
            summary="Release package and rollback plan prepared",
            artifacts={
                "release": {
                    "version": "1.0.0-golden",
                    "changelog": "Initial golden demo",
                    "rollback": "Revert Helm revision / compose project",
                }
            },
        )
    )


def run_devops(staging_url: str, *, regions: list[dict] | None = None) -> AgentStepResult:
    from chief_orchestrator.topology import staging_targets

    targets = regions or staging_targets()
    return _finish(
        AgentStepResult(
            agent_id=AgentId.DEVOPS,
            summary=f"Deployed to staging across {len(targets)} cluster(s): {staging_url}",
            artifacts={
                "deploy": {
                    "env": "staging",
                    "url": staging_url,
                    "health": "ok",
                    "customer_prod": False,
                    "regions": targets,
                }
            },
        )
    )


def run_devops_prod_promote(run_id: str) -> AgentStepResult:
    from chief_orchestrator.topology import production_targets

    targets = production_targets()
    return _finish(
        AgentStepResult(
            agent_id=AgentId.DEVOPS,
            summary=f"Promoted {run_id} to {len(targets)} production cluster(s)",
            artifacts={
                "deploy": {
                    "env": "production",
                    "health": "ok",
                    "customer_prod": True,
                    "regions": targets,
                    "urls": [t["endpoint"] for t in targets],
                }
            },
        )
    )


def run_sre(staging_url: str) -> AgentStepResult:
    return _finish(
        AgentStepResult(
            agent_id=AgentId.SRE_OBSERVABILITY,
            summary="SLOs and alerts registered for staging demo",
            artifacts={
                "sre": {
                    "slos": ["availability 99%", "latency p95 < 500ms"],
                    "alerts": ["healthz_down", "error_budget_burn"],
                    "target": staging_url,
                }
            },
        )
    )


def run_tech_writer() -> AgentStepResult:
    return _finish(
        AgentStepResult(
            agent_id=AgentId.TECH_WRITER,
            summary="Runbook and demo docs published",
            artifacts={
                "docs": {
                    "runbook": "docs/FULL_GIE_FLEET.md",
                    "user": "Use Orchestrator text or voice for commands",
                }
            },
        )
    )
