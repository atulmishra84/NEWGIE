"""Typer CLI for Context Intelligence Agent."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import httpx
import typer


app = typer.Typer(
    name="gie-context", help="GIE Context Intelligence CLI", no_args_is_help=True
)


def _headers(api_key: str | None, token: str | None) -> dict[str, str]:
    if api_key:
        return {"X-API-Key": api_key}
    if token:
        return {"Authorization": f"Bearer {token}"}
    typer.echo("Authentication required: --api-key or --token", err=True)
    raise typer.Exit(code=1)


@app.command("scan")
def scan(
    path: str = typer.Argument(..., help="Path to scan"),
    api_url: str = typer.Option("http://localhost:8080", envvar="GIE_API_URL"),
    api_key: str | None = typer.Option(None, envvar="GIE_API_KEY"),
    token: str | None = typer.Option(None, envvar="GIE_JWT_TOKEN"),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Write resulting model JSON to file"
    ),
    wait: bool = typer.Option(False, help="Poll until scan completes"),
) -> None:
    """Start a folder scan and optionally wait for the context model."""
    payload = {
        "source": {"type": "folder", "path": str(Path(path).resolve())},
        "idempotency_key": uuid4().hex,
    }
    headers = _headers(api_key, token)
    with httpx.Client(base_url=api_url, timeout=60.0) as client:
        resp = client.post("/v1/scans", json=payload, headers=headers)
        resp.raise_for_status()
        scan_data = resp.json()["data"]
        typer.echo(json.dumps(scan_data, indent=2))

        if not wait or not scan_data.get("scan_id"):
            return

        scan_id = scan_data["scan_id"]
        while True:
            status_resp = client.get(f"/v1/scans/{scan_id}", headers=headers)
            status_resp.raise_for_status()
            current = status_resp.json()["data"]
            if current["status"] in {"completed", "failed", "cancelled"}:
                if current["status"] != "completed" or not current.get("model_id"):
                    typer.echo(json.dumps(current, indent=2))
                    raise typer.Exit(code=2)
                model_resp = client.get(
                    f"/v1/context-models/{current['model_id']}", headers=headers
                )
                model_resp.raise_for_status()
                model_json = model_resp.json()["data"]
                if output:
                    output.write_text(json.dumps(model_json, indent=2))
                    typer.echo(f"Wrote model to {output}")
                else:
                    typer.echo(json.dumps(model_json, indent=2))
                return
            import time

            time.sleep(2)


@app.command("get-model")
def get_model(
    model_id: str = typer.Argument(...),
    api_url: str = typer.Option("http://localhost:8080", envvar="GIE_API_URL"),
    api_key: str | None = typer.Option(None, envvar="GIE_API_KEY"),
    token: str | None = typer.Option(None, envvar="GIE_JWT_TOKEN"),
    version: int | None = typer.Option(None),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Fetch a context model by ID."""
    headers = _headers(api_key, token)
    params = {"version": version} if version is not None else None
    with httpx.Client(base_url=api_url, timeout=30.0) as client:
        resp = client.get(
            f"/v1/context-models/{model_id}", headers=headers, params=params
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        text = json.dumps(data, indent=2)
        if output:
            output.write_text(text)
            typer.echo(f"Wrote model to {output}")
        else:
            typer.echo(text)


@app.callback()
def main_callback() -> None:
    """GIE Context Intelligence CLI."""


if __name__ == "__main__":
    app()
