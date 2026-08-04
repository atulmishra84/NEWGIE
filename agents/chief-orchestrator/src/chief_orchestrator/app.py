"""Chief Orchestrator FastAPI app — text + voice command surface."""

from __future__ import annotations

import base64
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from gie_contracts import Channel, CommandRequest, IntentType
from pydantic import BaseModel, Field

from chief_orchestrator import __version__
from chief_orchestrator.config import settings
from chief_orchestrator import jarvis as jarvis_bridge
from chief_orchestrator.pipeline import (
    build_go_no_go,
    handle_prod_approve,
    handle_status,
    run_change_request,
    run_golden,
    store,
)
from chief_orchestrator.registry import registry
from chief_orchestrator.topology import load_topology, production_targets
from chief_orchestrator.voice import normalize_intent, stt_from_audio, synthesize_tts


def _resolve_console_dir() -> Path | None:
    candidates: list[Path] = []
    if settings.console_dir:
        candidates.append(Path(settings.console_dir))
    here = Path(__file__).resolve()
    # .../agents/chief-orchestrator/src/chief_orchestrator/app.py → repo root
    candidates.extend(
        [
            here.parents[4] / "frontend" / "command-console",
            Path("/app/frontend/command-console"),
            Path("/workspace/frontend/command-console"),
        ]
    )
    for path in candidates:
        if (path / "index.html").is_file():
            return path
    return None


CONSOLE_DIR = _resolve_console_dir()


@asynccontextmanager
async def lifespan(_: FastAPI):
    registry.bootstrap()
    Path(settings.artifact_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="GIE Chief Orchestrator",
    version=__version__,
    description="Full+GIE fleet front door (text + voice + command console)",
    lifespan=lifespan,
)

_cors_origins = settings.cors_origin_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class JarvisConfigBody(BaseModel):
    enabled: bool = False
    webhook_url: str = ""
    token: str = ""


class JarvisForwardBody(BaseModel):
    event: dict[str, Any] = Field(default_factory=dict)


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {
        "status": "ok",
        "agent": "chief-orchestrator",
        "version": __version__,
        "console": bool(CONSOLE_DIR),
        "jarvis": jarvis_bridge.public_config().get("enabled", False),
    }


@app.get("/v1/integrations/jarvis")
async def jarvis_get() -> dict[str, Any]:
    return jarvis_bridge.public_config()


@app.put("/v1/integrations/jarvis")
async def jarvis_put(body: JarvisConfigBody) -> dict[str, Any]:
    return jarvis_bridge.save_config(
        enabled=body.enabled,
        webhook_url=body.webhook_url,
        token=body.token,
    )


@app.post("/v1/integrations/jarvis/forward")
async def jarvis_forward(body: JarvisForwardBody) -> dict[str, Any]:
    event = dict(body.event or {})
    event.setdefault("source", "gie-chief-orchestrator")
    return await jarvis_bridge.forward_event(event)


@app.get("/demo/golden")
async def demo_golden() -> dict[str, Any]:
    return {
        "status": "ok",
        "app": "golden-demo",
        "message": "Golden demo staging surface",
        "run_id": store.latest_golden_run_id,
    }


@app.get("/demo/golden/feature-x")
async def demo_feature_x() -> dict[str, Any]:
    return {"status": "ok", "feature": "X", "parent_run": store.latest_golden_run_id}


@app.get("/demo/prod/{region}")
async def demo_prod(region: str) -> dict[str, Any]:
    return {
        "status": "ok",
        "env": "production",
        "region": region,
        "run_id": store.latest_golden_run_id,
        "unsupervised": settings.unsupervised_prod,
    }


@app.get("/v1/topology")
async def topology() -> dict[str, Any]:
    return load_topology()


@app.get("/v1/fleet")
async def fleet() -> dict[str, Any]:
    return await handle_status()


@app.get("/v1/runs/{run_id}")
async def get_run(run_id: str) -> Any:
    run = store.runs.get(run_id)
    if not run:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return run.model_dump(mode="json")


@app.get("/v1/runs/{run_id}/trace")
async def get_run_trace(run_id: str) -> Any:
    run = store.runs.get(run_id)
    if not run:
        return JSONResponse({"error": "not_found"}, status_code=404)
    spans = store.get_trace(run_id)
    return {
        "run_id": run_id,
        "status": run.status.value,
        "span_count": len(spans),
        "spans": spans,
    }


@app.get("/v1/go-no-go")
async def go_no_go() -> dict[str, Any]:
    report = build_go_no_go().model_dump(mode="json")
    out = Path(settings.artifact_dir) / "go-no-go.api.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    return report


async def _dispatch(
    *,
    text: str,
    channel: Channel,
    inject_critical: bool = False,
    force_policy_deny: bool = False,
    prod_confirm_phrase: str | None = None,
) -> dict[str, Any]:
    intent = normalize_intent(
        text=text,
        channel=channel,
        prod_confirm_phrase=prod_confirm_phrase,
    )
    reply: dict[str, Any] = {
        "channel": channel.value,
        "transcript": text,
        "intent": intent.model_dump(mode="json"),
    }

    if intent.needs_clarification and intent.intent in {IntentType.CLARIFY, IntentType.UNKNOWN}:
        reply["status"] = "needs_clarification"
        reply["message"] = intent.clarification_prompt
        reply["run_started"] = False
        return reply

    if intent.intent == IntentType.STATUS:
        reply["status"] = "ok"
        reply["result"] = await handle_status()
        return reply

    if intent.intent == IntentType.PROD_APPROVE:
        if intent.needs_clarification:
            reply["status"] = "rejected"
            reply["result"] = await handle_prod_approve(intent)
            reply["message"] = intent.clarification_prompt
            return reply
        reply["status"] = "ok"
        reply["result"] = await handle_prod_approve(intent)
        return reply

    if intent.intent == IntentType.GOLDEN_RUN:
        run = await run_golden(
            intent,
            inject_critical=inject_critical,
            force_policy_deny=force_policy_deny,
        )
        reply["status"] = run.status.value
        reply["run"] = run.model_dump(mode="json")
        return reply

    if intent.intent == IntentType.CHANGE_REQUEST:
        run = await run_change_request(intent)
        reply["status"] = run.status.value
        reply["run"] = run.model_dump(mode="json")
        return reply

    reply["status"] = "needs_clarification"
    reply["message"] = intent.clarification_prompt
    reply["run_started"] = False
    return reply


@app.post("/v1/command")
async def command_text(body: CommandRequest) -> dict[str, Any]:
    text = (body.text or body.transcript or "").strip()
    result = await _dispatch(
        text=text,
        channel=body.channel or Channel.TEXT,
        inject_critical=body.inject_critical_finding,
        force_policy_deny=body.force_policy_deny,
        prod_confirm_phrase=body.prod_confirm_phrase,
    )
    if body.channel == Channel.VOICE:
        audio, provider = await synthesize_tts(result.get("message") or result.get("status", "ok"))
        result["tts_provider"] = provider
        result["tts_wav_base64"] = base64.b64encode(audio).decode("ascii")
    return result


@app.post("/v1/command/voice")
async def command_voice(
    transcript: str | None = Form(default=None),
    prod_confirm_phrase: str | None = Form(default=None),
    inject_critical_finding: bool = Form(default=False),
    force_policy_deny: bool = Form(default=False),
    audio: UploadFile | None = File(default=None),
) -> dict[str, Any]:
    audio_bytes = await audio.read() if audio is not None else None
    text, stt_provider = await stt_from_audio(transcript, audio_bytes)
    if not text:
        msg = (
            "Voice received but no transcript/STT result. "
            "Set ORCH_STT_PROVIDER=openai|deepgram with API keys, or pass transcript=."
        )
        audio_out, tts_provider = await synthesize_tts(msg)
        return {
            "channel": Channel.VOICE.value,
            "status": "needs_clarification",
            "message": msg,
            "run_started": False,
            "stt_provider": stt_provider,
            "tts_provider": tts_provider,
            "tts_wav_base64": base64.b64encode(audio_out).decode("ascii"),
        }

    result = await _dispatch(
        text=text,
        channel=Channel.VOICE,
        inject_critical=inject_critical_finding,
        force_policy_deny=force_policy_deny,
        prod_confirm_phrase=prod_confirm_phrase,
    )
    spoken = result.get("message") or result.get("status") or "done"
    if "run" in result and result["run"].get("evidence"):
        spoken = result["run"]["evidence"].get("demo_summary") or spoken
    audio_out, tts_provider = await synthesize_tts(str(spoken))
    result["stt_provider"] = stt_provider
    result["tts_provider"] = tts_provider
    result["tts_wav_base64"] = base64.b64encode(audio_out).decode("ascii")
    return result


@app.get("/v1/tts")
async def tts(text: str = "ok") -> Response:
    audio, _provider = await synthesize_tts(text)
    return Response(content=audio, media_type="audio/wav")


@app.get("/v1/prod/targets")
async def prod_targets() -> dict[str, Any]:
    return {"targets": production_targets()}


@app.get("/")
async def console_index() -> Any:
    if CONSOLE_DIR is None:
        return {
            "service": "gie-chief-orchestrator",
            "version": __version__,
            "docs": "/docs",
            "console": "not_bundled",
            "hint": "Open frontend/command-console/index.html or set ORCH_CONSOLE_DIR",
        }
    return FileResponse(CONSOLE_DIR / "index.html")


if CONSOLE_DIR is not None:
    app.mount("/console", StaticFiles(directory=str(CONSOLE_DIR), html=True), name="console")
