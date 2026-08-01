"""Real CVE scanner integrations (OSV + optional Snyk)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx

from gie_contracts import AgentId, Finding, Severity

from chief_orchestrator.config import settings

logger = logging.getLogger(__name__)

# Default packages for live/staging scans (current/stable versions).
_DEFAULT_PACKAGES = [
    {"ecosystem": "PyPI", "name": "requests", "version": "2.32.3"},
    {"ecosystem": "PyPI", "name": "httpx", "version": "0.27.2"},
]


def _severity_from_score(score: float | None) -> Severity:
    if score is None:
        return Severity.MEDIUM
    if score >= 9.0:
        return Severity.CRITICAL
    if score >= 7.0:
        return Severity.HIGH
    if score >= 4.0:
        return Severity.MEDIUM
    return Severity.LOW


def load_packages() -> list[dict[str, str]]:
    path = Path(settings.cve_manifest_path) if settings.cve_manifest_path else None
    if path and path.is_file():
        data = json.loads(path.read_text())
        if isinstance(data, list):
            return [p for p in data if isinstance(p, dict) and "name" in p]
    return list(_DEFAULT_PACKAGES)


async def scan_osv(packages: list[dict[str, str]] | None = None) -> list[Finding]:
    packages = packages or load_packages()
    findings: list[Finding] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for pkg in packages:
            body = {
                "package": {
                    "ecosystem": pkg.get("ecosystem", "PyPI"),
                    "name": pkg["name"],
                },
                "version": pkg.get("version", ""),
            }
            try:
                resp = await client.post(settings.osv_api_url, json=body)
                resp.raise_for_status()
                vulns = resp.json().get("vulns") or []
            except Exception as exc:  # noqa: BLE001
                logger.warning("OSV query failed for %s: %s", pkg.get("name"), exc)
                continue
            for vuln in vulns[:5]:
                sev = Severity.MEDIUM
                for s in vuln.get("severity") or []:
                    score = None
                    try:
                        score = float((s.get("score") or 0))
                    except (TypeError, ValueError):
                        score = None
                    mapped = _severity_from_score(score)
                    if mapped.value in {"critical", "high"}:
                        sev = mapped
                        break
                    sev = mapped
                finding_id = vuln.get("id") or "OSV-UNKNOWN"
                block_high = settings.cve_block_high
                blocking = sev == Severity.CRITICAL or (block_high and sev == Severity.HIGH)
                findings.append(
                    Finding(
                        source_agent=AgentId.VULNERABILITY_ENGINEER,
                        severity=sev,
                        title=f"OSV {finding_id}: {pkg['name']}",
                        detail=(vuln.get("summary") or "")[:500],
                        blocking=blocking,
                    )
                )
    return findings


async def scan_snyk(packages: list[dict[str, str]] | None = None) -> list[Finding]:
    if not settings.snyk_token:
        return []
    packages = packages or load_packages()
    findings: list[Finding] = []
    headers = {
        "Authorization": f"token {settings.snyk_token}",
        "content-type": "application/json",
    }
    # Snyk Test API varies by ecosystem; use issues search-style stub endpoint pattern
    # with graceful degrade when org/API shape differs.
    async with httpx.AsyncClient(timeout=30.0) as client:
        for pkg in packages:
            eco = (pkg.get("ecosystem") or "PyPI").lower()
            package_manager = "pip" if eco == "pypi" else "npm"
            url = f"https://api.snyk.io/v1/test/{package_manager}/{pkg['name']}/{pkg.get('version', 'latest')}"
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code >= 400:
                    logger.warning("Snyk HTTP %s for %s", resp.status_code, pkg["name"])
                    continue
                issues = (resp.json().get("issues") or {}).get("vulnerabilities") or []
            except Exception as exc:  # noqa: BLE001
                logger.warning("Snyk query failed for %s: %s", pkg.get("name"), exc)
                continue
            for issue in issues[:5]:
                severity = str(issue.get("severity") or "medium").lower()
                sev = {
                    "critical": Severity.CRITICAL,
                    "high": Severity.HIGH,
                    "medium": Severity.MEDIUM,
                    "low": Severity.LOW,
                }.get(severity, Severity.MEDIUM)
                blocking = sev == Severity.CRITICAL or (
                    settings.cve_block_high and sev == Severity.HIGH
                )
                findings.append(
                    Finding(
                        source_agent=AgentId.VULNERABILITY_ENGINEER,
                        severity=sev,
                        title=f"Snyk {issue.get('id', 'issue')}: {pkg['name']}",
                        detail=str(issue.get("title") or "")[:500],
                        blocking=blocking,
                    )
                )
    return findings


async def run_cve_providers(*, inject_critical: bool = False) -> tuple[list[Finding], dict[str, Any]]:
    packages = load_packages()
    findings: list[Finding] = []
    meta: dict[str, Any] = {"providers": [], "packages": packages}

    if inject_critical:
        findings.append(
            Finding(
                source_agent=AgentId.VULNERABILITY_ENGINEER,
                severity=Severity.CRITICAL,
                title="Injected critical dependency vulnerability",
                detail="Live-test fixture LT-3.1",
                blocking=True,
            )
        )
        meta["providers"].append("fixture")

    for provider in settings.cve_provider_list:
        if provider == "osv":
            osv_findings = await scan_osv(packages)
            findings.extend(osv_findings)
            meta["providers"].append({"name": "osv", "count": len(osv_findings)})
        elif provider == "snyk":
            snyk_findings = await scan_snyk(packages)
            findings.extend(snyk_findings)
            meta["providers"].append({"name": "snyk", "count": len(snyk_findings)})

    if not findings and not inject_critical:
        findings.append(
            Finding(
                source_agent=AgentId.VULNERABILITY_ENGINEER,
                severity=Severity.INFO,
                title="CVE scan completed with no blocking findings",
                detail=f"Providers={settings.cve_provider_list}",
                blocking=False,
            )
        )
    return findings, meta
