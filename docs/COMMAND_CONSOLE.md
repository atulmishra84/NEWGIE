# GIE Command Console

Simple browser UI to send commands to the Chief Orchestrator, watch fleet activity, and optionally forward events to JARVIS.

## Open it

With the orchestrator running:

| Setup | URL |
| --- | --- |
| Mac stack (orchestrator on 8091) | http://127.0.0.1:8091/ |
| Full+GIE docker compose (orchestrator on 8090) | http://127.0.0.1:8090/ |
| Static files only | open `frontend/command-console/index.html` and set Orchestrator URL |

Also available at `/console/` when the frontend is bundled.

## Use it

1. Confirm the badge shows **Connected**.
2. Type a command, e.g. `status` or `run golden demo`.
3. Watch **Activity** and **Latest result** update.
4. Use **Refresh fleet** to see registered agents.

Voice uses the browser speech API (Chrome/Edge). The orchestrator also exposes `/v1/command/voice` for server-side STT/TTS.

## JARVIS integration

1. Enable **Forward commands & results to JARVIS**.
2. Set your JARVIS webhook URL (example: `http://127.0.0.1:7xxx/v1/gie/events`).
3. Optionally set a bearer token.
4. Click **Save**, then **Test ping**.

Events are posted as JSON:

```json
{
  "source": "gie-command-console",
  "ts": "2026-08-04T10:00:00.000Z",
  "type": "command.accepted",
  "text": "run golden demo",
  "run_id": "run_...",
  "status": "completed"
}
```

Common `type` values: `ping`, `command.accepted`, `run.event`, `run.finished`.

### Server-side relay (recommended)

The orchestrator exposes:

- `GET /v1/integrations/jarvis` — current config (token redacted)
- `PUT /v1/integrations/jarvis` — save `{enabled, webhook_url, token}`
- `POST /v1/integrations/jarvis/forward` — relay `{event: {...}}`

Env defaults:

```bash
ORCH_JARVIS_ENABLED=false
ORCH_JARVIS_WEBHOOK_URL=
ORCH_JARVIS_TOKEN=
ORCH_CONSOLE_DIR=/app/frontend/command-console
ORCH_CORS_ORIGINS=*
```

Server relay avoids browser CORS issues when JARVIS does not allow cross-origin posts.
