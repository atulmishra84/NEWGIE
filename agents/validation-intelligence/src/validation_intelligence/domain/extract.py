"""Normalize policy payloads from packages/artifacts/content."""

from __future__ import annotations

import json
from typing import Any

import yaml

from gie_contracts.validation import ValidationInputBundle


def collect_documents(bundle: ValidationInputBundle) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    pkg = bundle.policy_package or {}
    for p in pkg.get("policies") or bundle.policies or []:
        if isinstance(p, dict):
            docs.append(
                {
                    "filename": p.get("filename")
                    or p.get("metadata", {}).get("name")
                    or "policy.json",
                    "format": p.get("format") or bundle.format or "json",
                    "content": p.get("content") or "",
                    "body": p.get("body") or {},
                }
            )
    for a in pkg.get("artifacts") or bundle.artifacts or []:
        if isinstance(a, dict):
            docs.append(
                {
                    "filename": a.get("filename") or "artifact",
                    "format": a.get("format") or _guess_format(a.get("filename") or ""),
                    "content": a.get("content") or "",
                    "body": {},
                }
            )
    named = pkg.get("named_artifacts") or {}
    if isinstance(named, dict):
        for fname, content in named.items():
            docs.append(
                {
                    "filename": fname,
                    "format": _guess_format(fname),
                    "content": content or "",
                    "body": {},
                }
            )
    if bundle.content:
        docs.append(
            {
                "filename": bundle.filename or "inline",
                "format": bundle.format or _guess_format(bundle.filename or ""),
                "content": bundle.content,
                "body": {},
            }
        )
    if not docs:
        docs.append(
            {"filename": "empty", "format": "json", "content": "{}", "body": {}}
        )
    # parse bodies
    for d in docs:
        if d["body"]:
            continue
        content = d["content"]
        fmt = str(d["format"]).lower()
        try:
            if fmt in {
                "json",
                "openai_guardrails",
                "azure_ai_foundry",
                "langgraph",
                "crewai",
                "autogen",
                "semantic_kernel",
                "api_gateway",
                "prompt",
                "identity",
                "runtime",
                "dlp",
            } or (content.lstrip().startswith("{")):
                d["body"] = json.loads(content) if content.strip() else {}
            elif (
                fmt in {"yaml", "kubernetes", "admission_controller"}
                or "apiVersion:" in content[:200]
            ):
                d["body"] = yaml.safe_load(content) or {}
            elif fmt in {"opa_rego", "rego"} or d["filename"].endswith(".rego"):
                d["body"] = {"rego": content}
            else:
                d["body"] = {"raw": content}
        except Exception as exc:  # noqa: BLE001
            d["body"] = {"_parse_error": str(exc), "raw": content}
            d["parse_error"] = str(exc)
    return docs


def _guess_format(filename: str) -> str:
    f = filename.lower()
    if f.endswith(".rego"):
        return "opa_rego"
    if f.endswith((".yaml", ".yml")):
        return "yaml"
    if f.endswith(".tf"):
        return "terraform"
    if f.endswith(".json"):
        return "json"
    if f.endswith(".co"):
        return "nvidia_nemo"
    return "json"


def extract_rules(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for d in docs:
        body = d.get("body") or {}
        # nested spec.rules / rules / steps
        candidates = []
        if isinstance(body.get("rules"), dict):
            for k, v in body["rules"].items():
                candidates.append({"id": k, "value": v, "source": d["filename"]})
        if isinstance(body.get("spec"), dict) and isinstance(
            body["spec"].get("rules"), dict
        ):
            for k, v in body["spec"]["rules"].items():
                candidates.append({"id": k, "value": v, "source": d["filename"]})
        for step in body.get("steps") or []:
            if isinstance(step, dict):
                candidates.append(
                    {
                        "id": step.get("type") or str(step),
                        "value": step,
                        "source": d["filename"],
                    }
                )
        controls = (
            body.get("controls") or (body.get("spec") or {}).get("controls") or []
        )
        for c in controls:
            candidates.append({"id": str(c), "value": True, "source": d["filename"]})
        if body.get("rego"):
            candidates.append(
                {
                    "id": "rego.allow",
                    "value": "allow" in str(body["rego"]),
                    "source": d["filename"],
                }
            )
        rules.extend(candidates)
    return rules
