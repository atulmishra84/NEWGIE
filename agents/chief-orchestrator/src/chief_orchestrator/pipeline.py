"""Multi-lane pipeline for golden runs, change requests, and prod gates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gie_contracts import (
    Channel,
    EvidencePackage,
    Finding,
    FleetRun,
    GoNoGoReport,
    IntentType,
    NormalizedIntent,
    PolicyDecision,
    RunStatus,
)

from chief_orchestrator import roles
from chief_orchestrator.config import settings
from chief_orchestrator import gie_client
from chief_orchestrator.registry import registry


class PipelineStore:
    def __init__(self) -> None:
        self.runs: dict[str, FleetRun] = {}
        self.traces: dict[str, list[dict[str, Any]]] = {}
        self.latest_golden_run_id: str | None = None
        self.live_checks: dict[str, bool] = {}

    def save(self, run: FleetRun) -> FleetRun:
        run.touch()
        self.runs[run.run_id] = run
        return run

    def add_trace(self, run_id: str, event: str, **details: Any) -> None:
        self.traces.setdefault(run_id, []).append(
            {"event": event, "details": details}
        )

    def get_trace(self, run_id: str) -> list[dict[str, Any]]:
        return list(self.traces.get(run_id, []))


store = PipelineStore()


async def handle_status() -> dict[str, Any]:
    from chief_orchestrator.topology import load_topology, production_targets, staging_targets

    registry.touch_all()
    platform = await gie_client.refresh_platform_health()
    agents = [a.model_dump(mode="json") for a in registry.list_agents()]
    topo = load_topology()
    return {
        "fleet_size": registry.expected_count(),
        "healthy": registry.healthy_count(),
        "platform": platform,
        "agents": agents,
        "staging_base_url": settings.staging_base_url,
        "voice": {
            "stt": True,
            "tts": True,
            "stt_provider": settings.stt_provider,
            "tts_provider": settings.tts_provider,
        },
        "customer_prod_enabled": settings.allow_customer_prod,
        "unsupervised_prod": settings.unsupervised_prod,
        "cve_providers": settings.cve_provider_list,
        "regions": {
            "staging": staging_targets(topo),
            "production": production_targets(topo),
        },
    }


def _collect_findings(run: FleetRun) -> list[Finding]:
    findings: list[Finding] = []
    for step in run.steps:
        findings.extend(step.findings)
    run.findings = findings
    return findings


async def run_golden(
    intent: NormalizedIntent,
    *,
    inject_critical: bool = False,
    force_policy_deny: bool = False,
) -> FleetRun:
    run = FleetRun(
        status=RunStatus.RUNNING,
        intent=IntentType.GOLDEN_RUN,
        channel=intent.channel,
        command_text=intent.text,
    )
    store.save(run)
    store.add_trace(run.run_id, "run_started", intent=intent.intent.value, channel=intent.channel.value)
    registry.touch_all()
    store.add_trace(run.run_id, "fleet_heartbeats", healthy=registry.healthy_count())

    pm = roles.run_product_manager(intent.text)
    run.steps.append(pm)
    store.add_trace(run.run_id, "step", agent=pm.agent_id.value, ok=pm.ok)
    ux = roles.run_ux_designer(pm.artifacts["prd"])
    run.steps.append(ux)
    store.add_trace(run.run_id, "step", agent=ux.agent_id.value, ok=ux.ok)
    lead = roles.run_senior_developer(intent.text)
    run.steps.append(lead)
    store.add_trace(run.run_id, "step", agent=lead.agent_id.value, ok=lead.ok)
    fe = roles.run_frontend(ux.artifacts["ux"])
    run.steps.append(fe)
    store.add_trace(run.run_id, "step", agent=fe.agent_id.value, ok=fe.ok)
    be = roles.run_backend(lead.artifacts["architecture"])
    run.steps.append(be)
    store.add_trace(run.run_id, "step", agent=be.agent_id.value, ok=be.ok)

    appsec = roles.run_appsec()
    run.steps.append(appsec)
    store.add_trace(run.run_id, "step", agent=appsec.agent_id.value, ok=appsec.ok)
    vuln = await roles.run_vuln_eng(inject_critical=inject_critical)
    run.steps.append(vuln)
    store.add_trace(run.run_id, "step", agent=vuln.agent_id.value, ok=vuln.ok)
    sec = roles.run_sec_test(inject_critical=inject_critical)
    run.steps.append(sec)
    store.add_trace(run.run_id, "step", agent=sec.agent_id.value, ok=sec.ok)
    comp = roles.run_compliance()
    run.steps.append(comp)
    store.add_trace(run.run_id, "step", agent=comp.agent_id.value, ok=comp.ok)

    findings = _collect_findings(run)
    blocking = [f for f in findings if f.blocking]

    if any(f.blocking for f in findings):
        run.status = RunStatus.BLOCKED
        run.blocked_reason = "Critical/high security findings block staging promote"
        run.evidence = EvidencePackage(
            run_id=run.run_id,
            demo_summary="Blocked by security gate",
            reports={"findings": [f.model_dump(mode="json") for f in findings]},
            voice_transcripts=[intent.text] if intent.channel == Channel.VOICE else [],
        )
        store.add_trace(run.run_id, "gate_blocked", reason=run.blocked_reason)
        store.save(run)
        return run

    acceptance = list(pm.artifacts.get("acceptance") or pm.artifacts.get("prd", {}).get("acceptance") or [])
    qa = roles.run_qa(acceptance)
    run.steps.append(qa)
    store.add_trace(run.run_id, "step", agent=qa.agent_id.value, ok=qa.ok)
    rel = roles.run_release_manager()
    run.steps.append(rel)
    store.add_trace(run.run_id, "step", agent=rel.agent_id.value, ok=rel.ok)
    staging_url = settings.golden_staging_url
    devops = roles.run_devops(staging_url)
    run.steps.append(devops)
    store.add_trace(run.run_id, "step", agent=devops.agent_id.value, ok=devops.ok)
    sre = roles.run_sre(staging_url)
    run.steps.append(sre)
    store.add_trace(run.run_id, "step", agent=sre.agent_id.value, ok=sre.ok)
    docs = roles.run_tech_writer()
    run.steps.append(docs)
    store.add_trace(run.run_id, "step", agent=docs.agent_id.value, ok=docs.ok)

    context = await gie_client.scan_context_stub(intent.text)
    store.add_trace(run.run_id, "gie_context", model_id=context.get("model_id"), source=context.get("source"))
    risk = await gie_client.assess_risk(
        context_model_id=context["model_id"],
        blocking_findings=len(blocking),
        force_high=force_policy_deny,
    )
    store.add_trace(run.run_id, "gie_risk", score=risk.score, level=risk.level.value)
    policy = await gie_client.evaluate_policy(risk=risk, force_deny=force_policy_deny)
    store.add_trace(run.run_id, "gie_policy", decision=policy.decision.value)

    if policy.decision == PolicyDecision.DENY:
        run.status = RunStatus.BLOCKED
        run.blocked_reason = "GIE Policy denied deploy: " + "; ".join(policy.reasons)
        run.evidence = EvidencePackage(
            run_id=run.run_id,
            staging_url=None,
            demo_summary="Policy deny",
            acceptance=acceptance,
            gie_context_model_id=context["model_id"],
            risk=risk,
            policy=policy,
            reports={"context": context},
            voice_transcripts=[intent.text] if intent.channel == Channel.VOICE else [],
        )
        store.add_trace(run.run_id, "gate_blocked", reason=run.blocked_reason)
        store.save(run)
        return run

    Path(settings.artifact_dir).mkdir(parents=True, exist_ok=True)
    evidence = EvidencePackage(
        run_id=run.run_id,
        pr_url=f"https://github.com/gie/fleet/pull/{run.run_id[-6:]}",
        staging_url=staging_url,
        demo_summary="Golden demo deployed to staging with Full+GIE evidence package",
        acceptance=acceptance,
        gie_context_model_id=context["model_id"],
        risk=risk,
        policy=policy,
        reports={
            "context": context,
            "release": rel.artifacts,
            "findings": [f.model_dump(mode="json") for f in findings],
            "trace_events": len(store.get_trace(run.run_id)),
        },
        voice_transcripts=[intent.text] if intent.channel == Channel.VOICE else [],
    )
    run.evidence = evidence
    run.status = RunStatus.SUCCEEDED
    run.human_approval_required = not (
        settings.allow_customer_prod and settings.unsupervised_prod
    )
    store.latest_golden_run_id = run.run_id
    store.add_trace(run.run_id, "run_succeeded", staging_url=staging_url)

    if settings.allow_customer_prod and settings.unsupervised_prod:
        promote = roles.run_devops_prod_promote(run.run_id)
        run.steps.append(promote)
        store.add_trace(
            run.run_id,
            "unsupervised_prod_promote",
            regions=promote.artifacts.get("deploy", {}).get("regions", []),
        )
        evidence.reports["prod_promote"] = promote.artifacts
        evidence.demo_summary += " | Unsupervised multi-region prod promote complete"
        run.human_approved = True

    store.save(run)
    return run


async def run_change_request(intent: NormalizedIntent) -> FleetRun:
    base = store.latest_golden_run_id
    run = FleetRun(
        status=RunStatus.RUNNING,
        intent=IntentType.CHANGE_REQUEST,
        channel=intent.channel,
        command_text=intent.text,
    )
    store.save(run)
    registry.touch_all()

    pm = roles.run_product_manager(f"Delta: {intent.text}")
    run.steps.append(pm)
    lead = roles.run_senior_developer(intent.text)
    run.steps.append(lead)
    run.steps.append(roles.run_frontend({"primary_flow": ["Landing", "Feature X", "Status"]}))
    run.steps.append(roles.run_backend(lead.artifacts["architecture"]))
    acceptance = list(pm.artifacts.get("acceptance") or []) + ["Feature X visible"]
    run.steps.append(roles.run_qa(acceptance))
    staging_url = settings.golden_staging_url + "/feature-x"
    run.steps.append(roles.run_devops(staging_url))

    context = await gie_client.scan_context_stub(intent.text)
    risk = await gie_client.assess_risk(context_model_id=context["model_id"], blocking_findings=0)
    policy = await gie_client.evaluate_policy(risk=risk, force_deny=False)

    run.evidence = EvidencePackage(
        run_id=run.run_id,
        pr_url=f"https://github.com/gie/fleet/pull/{run.run_id[-6:]}",
        staging_url=staging_url,
        demo_summary=f"Change applied on top of {base or 'baseline'}",
        acceptance=pm.artifacts["prd"]["acceptance"],
        gie_context_model_id=context["model_id"],
        risk=risk,
        policy=policy,
        reports={"parent_run": base, "context": context},
        voice_transcripts=[intent.text] if intent.channel == Channel.VOICE else [],
    )
    run.status = RunStatus.SUCCEEDED
    run.human_approval_required = True
    store.save(run)
    return run


async def handle_prod_approve(intent: NormalizedIntent) -> dict[str, Any]:
    # Unsupervised mode: confirm phrase optional when already auto-promoted path is enabled
    if settings.allow_customer_prod and settings.unsupervised_prod:
        promote = roles.run_devops_prod_promote(store.latest_golden_run_id or "unknown")
        return {
            "approved": True,
            "status": "promoted_unsupervised",
            "customer_prod_touched": True,
            "human_gate": False,
            "unsupervised": True,
            "promote_artifacts_from": store.latest_golden_run_id,
            "regions": promote.artifacts.get("deploy", {}).get("regions", []),
            "urls": promote.artifacts.get("deploy", {}).get("urls", []),
        }

    if intent.needs_clarification or not intent.prod_confirmed:
        return {
            "approved": False,
            "status": "rejected",
            "reason": intent.clarification_prompt
            or "Production approve requires explicit confirmation phrase",
            "customer_prod_touched": False,
        }

    if not settings.allow_customer_prod:
        return {
            "approved": True,
            "status": "awaiting_human_dry_run",
            "reason": "Confirm accepted; customer prod disabled (set ORCH_ALLOW_CUSTOMER_PROD=true)",
            "customer_prod_touched": False,
            "human_gate": True,
            "promote_artifacts_from": store.latest_golden_run_id,
        }

    promote = roles.run_devops_prod_promote(store.latest_golden_run_id or "unknown")
    return {
        "approved": True,
        "status": "promoted",
        "customer_prod_touched": True,
        "human_gate": False,
        "unsupervised": False,
        "promote_artifacts_from": store.latest_golden_run_id,
        "regions": promote.artifacts.get("deploy", {}).get("regions", []),
        "urls": promote.artifacts.get("deploy", {}).get("urls", []),
    }


def build_go_no_go() -> GoNoGoReport:
    checks = {
        "fleet_registered": registry.healthy_count() >= min(16, registry.expected_count()),
        "has_golden_run": store.latest_golden_run_id is not None,
        **store.live_checks,
    }
    if store.latest_golden_run_id:
        run = store.runs.get(store.latest_golden_run_id)
        checks["golden_succeeded"] = bool(run and run.status == RunStatus.SUCCEEDED)
        checks["policy_allow"] = bool(
            run and run.evidence and run.evidence.policy and run.evidence.policy.decision == PolicyDecision.ALLOW
        )
    failed = [k for k, v in checks.items() if not v]
    demo = None
    if store.latest_golden_run_id and store.runs.get(store.latest_golden_run_id):
        ev = store.runs[store.latest_golden_run_id].evidence
        demo = ev.staging_url if ev else None
    return GoNoGoReport(
        ready_for_prod_approve=len(failed) == 0,
        staging_live=True,
        checks=checks,
        failed_checks=failed,
        demo_url=demo,
        evidence_run_id=store.latest_golden_run_id,
        summary="GO" if not failed else f"NO-GO: {', '.join(failed)}",
    )
