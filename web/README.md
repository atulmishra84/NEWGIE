# GIE Web

Static landing page and operations dashboard for the Guardrails Intelligence Engine.

## Pages

| File | Purpose |
|------|---------|
| `index.html` | Marketing landing |
| `dashboard.html` | Orchestrator console (`/analyze`, status, local history) |

## Preview locally

From this directory:

```bash
python3 -m http.server 5173
```

Open:

- Landing: http://127.0.0.1:5173/
- Dashboard: http://127.0.0.1:5173/dashboard.html

Point the dashboard **API base** at a running Orchestrator (default `http://127.0.0.1:8091`). Browser CORS must allow the origin; for local smoke, serve the API with permissive CORS or open the dashboard from the same host via a reverse proxy.

## Azure sandbox

Full deploy builds `web/Dockerfile` into ACR and exposes `gie-web` as a LoadBalancer. See [deploy/azure/README.md](../deploy/azure/README.md).

## Design notes

- Cool navy / teal system (Syne + Manrope + IBM Plex Mono)
- Landing is brand-first with a full-bleed mesh hero
- Dashboard is a functional console, not a marketing layout
