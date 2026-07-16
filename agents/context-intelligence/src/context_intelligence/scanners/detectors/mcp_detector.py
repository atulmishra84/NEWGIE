"""MCP server configuration detection."""

from __future__ import annotations

import json
from pathlib import Path

from context_intelligence.domain.findings import FindingCategory, FindingSection
from context_intelligence.scanners.detectors.base import BaseDetector, read_text
from context_intelligence.scanners.registry import DEFAULT_DETECTOR_REGISTRY

MCP_FILENAMES = {"mcp.json", "mcp_config.json"}
CURSOR_MCP_PATHS = (".cursor/mcp.json", ".cursor/mcp_config.json")


@DEFAULT_DETECTOR_REGISTRY.register_detector()
class McpDetector(BaseDetector):
    detector_id = "mcp.detector.v1"
    section = FindingSection.INTERFACES
    default_category = FindingCategory.MCP_SERVER

    async def detect(self, workspace_path: Path) -> list:
        findings = []
        candidates: list[Path] = []

        for name in MCP_FILENAMES:
            candidates.extend(workspace_path.rglob(name))
        for rel in CURSOR_MCP_PATHS:
            p = workspace_path / rel
            if p.is_file():
                candidates.append(p)

        for path in workspace_path.rglob("*.json"):
            if path.name in {"settings.json", "claude_desktop_config.json"}:
                candidates.append(path)

        seen: set[str] = set()
        for path in candidates:
            key = str(path)
            if key in seen or not path.is_file():
                continue
            seen.add(key)
            text = read_text(path)
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue

            servers = _extract_mcp_servers(data)
            for server_name, config in servers.items():
                findings.append(
                    self.finding(
                        name=server_name,
                        confidence=0.92,
                        rationale="MCP server configuration",
                        path=str(path),
                        attributes={"config": _redact_config(config)},
                    )
                )
        return findings


def _extract_mcp_servers(data: object) -> dict[str, object]:
    if not isinstance(data, dict):
        return {}
    if "mcpServers" in data and isinstance(data["mcpServers"], dict):
        return data["mcpServers"]
    if "mcp_servers" in data and isinstance(data["mcp_servers"], dict):
        return data["mcp_servers"]
    return {}


def _redact_config(config: object) -> object:
    if isinstance(config, dict):
        redacted = {}
        for key, value in config.items():
            if any(s in key.lower() for s in ("token", "secret", "password", "key")):
                redacted[key] = "<redacted>"
            else:
                redacted[key] = _redact_config(value)
        return redacted
    return config
