#!/usr/bin/env python3
"""Live-test LT-1..LT-5 against Full+GIE Chief Orchestrator."""

from __future__ import annotations

import json
import os
import struct
import sys
import tempfile
import urllib.error
import urllib.request
import wave
from typing import Any

ORCH = os.environ.get("ORCH_URL", "http://127.0.0.1:8090").rstrip("/")
PASS = 0
FAIL = 0
FAILED: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        print(f"PASS  {name}")
        PASS += 1
    else:
        print(f"FAIL  {name} {detail}")
        FAIL += 1
        FAILED.append(name)


def http_json(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"{ORCH}{path}",
        data=data,
        method=method,
        headers={"content-type": "application/json"} if body is not None else {},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def http_multipart(path: str, fields: dict[str, str], wav_path: str) -> dict[str, Any]:
    import uuid

    boundary = f"----gie{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    with open(wav_path, "rb") as f:
        audio = f.read()
    chunks.append(f"--{boundary}\r\n".encode())
    chunks.append(
        b'Content-Disposition: form-data; name="audio"; filename="sample.wav"\r\n'
        b"Content-Type: audio/wav\r\n\r\n"
    )
    chunks.append(audio)
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    body = b"".join(chunks)
    req = urllib.request.Request(
        f"{ORCH}{path}",
        data=body,
        method="POST",
        headers={"content-type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def make_wav(path: str) -> None:
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(struct.pack("<h", 0) * 1600)


def main() -> int:
    print(f"==> Live testing Orchestrator at {ORCH}")
    try:
        http_json("GET", "/healthz")
    except urllib.error.URLError as exc:
        print(f"Orchestrator not reachable: {exc}")
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "sample.wav")
        make_wav(wav)

        print("==> LT-1 Ingress")
        status = http_json("POST", "/v1/command", {"text": "status", "channel": "text"})
        check("LT-1.1 text status", "fleet_size" in status.get("result", {}))

        voice = http_multipart("/v1/command/voice", {"transcript": "status"}, wav)
        check("LT-1.2 voice status + tts", "tts_wav_base64" in voice and "result" in voice)

        ambig = http_multipart("/v1/command/voice", {"transcript": "ummm"}, wav)
        check(
            "LT-1.3 ambiguous voice no build",
            ambig.get("status") == "needs_clarification" and "run" not in ambig,
        )

        print("==> LT-2 Golden run")
        golden = http_json(
            "POST",
            "/v1/command",
            {
                "text": (
                    "Build the golden demo app, run full security and QA, "
                    "scan with GIE, deploy to staging, and show me the result."
                ),
                "channel": "text",
            },
        )
        steps = {s["agent_id"] for s in golden.get("run", {}).get("steps", [])}
        check("LT-2.1 delivery steps", {"product-manager", "senior-developer", "frontend-specialist"} <= steps)
        check(
            "LT-2.2 security lane",
            {"security-engineer", "vulnerability-engineer", "security-test-engineer", "compliance-officer"}
            <= steps,
        )
        check("LT-2.3 release/ops", {"qa-engineer", "devops", "sre-observability", "tech-writer"} <= steps)
        ev = golden.get("run", {}).get("evidence") or {}
        check("LT-2.4 GIE context model", bool(ev.get("gie_context_model_id")))
        check("LT-2.5 risk and policy", bool(ev.get("risk") and ev.get("policy")))
        check(
            "LT-2.6 demo package",
            golden.get("status") == "succeeded" and bool(ev.get("staging_url") and ev.get("pr_url")),
        )

        print("==> LT-3 Gates")
        crit = http_json(
            "POST",
            "/v1/command",
            {
                "text": (
                    "Build the golden demo app, run full security and QA, "
                    "scan with GIE, deploy to staging, and show me the result."
                ),
                "channel": "text",
                "inject_critical_finding": True,
            },
        )
        check("LT-3.1 critical blocks", crit.get("status") == "blocked")

        deny = http_json(
            "POST",
            "/v1/command",
            {
                "text": (
                    "Build the golden demo app, run full security and QA, "
                    "scan with GIE, deploy to staging, and show me the result."
                ),
                "channel": "text",
                "force_policy_deny": True,
            },
        )
        reason = (deny.get("run") or {}).get("blocked_reason") or ""
        check("LT-3.2 policy deny", deny.get("status") == "blocked" and "policy" in reason.lower())

        noconf = http_multipart(
            "/v1/command/voice",
            {"transcript": "approve production please"},
            wav,
        )
        check(
            "LT-3.3 voice prod without confirm rejected",
            noconf.get("status") in {"rejected", "needs_clarification"}
            or "confirm" in json.dumps(noconf).lower(),
        )

        dry = http_json(
            "POST",
            "/v1/command",
            {
                "text": "approve production deploy",
                "channel": "text",
                "prod_confirm_phrase": "approve production deploy",
            },
        )
        check(
            "LT-3.4 prod dry-run no customer prod",
            dry.get("result", {}).get("customer_prod_touched") is False
            and dry.get("result", {}).get("human_gate") is True,
        )

        print("==> LT-4 Change request")
        chg = http_json(
            "POST",
            "/v1/command",
            {"text": "Add a small feature X to the golden app", "channel": "text"},
        )
        chg_url = ((chg.get("run") or {}).get("evidence") or {}).get("staging_url") or ""
        check("LT-4.1 change request succeeds", chg.get("status") == "succeeded" and "feature-x" in chg_url)
        demo = http_json("GET", "/demo/golden")
        check("LT-4.2 demo healthy", demo.get("status") == "ok")

        print("==> LT-5 Audit / registry")
        run_id = (golden.get("run") or {}).get("run_id")
        trace = http_json("GET", f"/v1/runs/{run_id}/trace") if run_id else {}
        check(
            "LT-5.1 end-to-end trace",
            int(trace.get("span_count") or 0) >= 5
            and any(s.get("event") == "run_succeeded" for s in trace.get("spans", [])),
        )
        voice2 = http_multipart("/v1/command/voice", {"transcript": "status"}, wav)
        check("LT-5.2 voice transcript", voice2.get("transcript") == "status")
        # Voice transcripts on golden evidence when channel=voice; text golden still audited via command log
        golden_voice = http_multipart(
            "/v1/command/voice",
            {
                "transcript": (
                    "Build the golden demo app, run full security and QA, "
                    "scan with GIE, deploy to staging, and show me the result."
                )
            },
            wav,
        )
        gv_ev = (golden_voice.get("run") or {}).get("evidence") or {}
        check(
            "LT-5.2b voice transcript on run evidence",
            bool(gv_ev.get("voice_transcripts")),
        )
        fleet = http_json("GET", "/v1/fleet")
        check(
            "LT-5.3 agent registry >= 16",
            fleet.get("fleet_size", 0) >= 16 and fleet.get("healthy", 0) >= 16,
        )

        gng = http_json("GET", "/v1/go-no-go")
        print("==> Go/No-Go")
        print(json.dumps(gng, indent=2))
        artifact_dir = os.environ.get("ORCH_ARTIFACT_DIR", "/tmp/gie-fleet-artifacts")
        os.makedirs(artifact_dir, exist_ok=True)
        with open(os.path.join(artifact_dir, "go-no-go.json"), "w", encoding="utf-8") as fh:
            json.dump(gng, fh, indent=2)
        with open(os.path.join(artifact_dir, "live-test-summary.json"), "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "passed": PASS,
                    "failed": FAIL,
                    "failed_checks": FAILED,
                    "go_no_go": gng,
                    "demo_url": gng.get("demo_url"),
                },
                fh,
                indent=2,
            )

    print(f"\nPassed: {PASS}  Failed: {FAIL}")
    if FAIL:
        print("Failed:", ", ".join(FAILED))
        return 1
    print("LIVE_TEST_GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
