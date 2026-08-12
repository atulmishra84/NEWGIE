from __future__ import annotations
import asyncio
from typing import Optional
import typer
from rich import print as rprint
from gie_contracts.integration import (
    AuthMethod,
    AuthTokenRequest,
    ConnectRequest,
    PlatformId,
    SyncRequest,
)
from integration_intelligence.infrastructure.bootstrap import build_container
from integration_intelligence.settings import Settings
from integration_intelligence.domain.catalog import platform_catalog

app = typer.Typer(name="gie-integrate", help="GIE Integration Intelligence CLI")


def _run(coro):
    return asyncio.run(coro)


@app.command("platforms")
def platforms():
    """List supported platforms."""
    for p in platform_catalog():
        rprint(f"[bold]{p.platform_id.value}[/bold] — {p.name} ({p.category.value})")


@app.command("connect")
def connect(
    platform: str = typer.Argument(...),
    tenant: str = typer.Option("default", "--tenant"),
    name: str = typer.Option(..., "--name"),
    auth: str = typer.Option("api_key", "--auth"),
    api_key: Optional[str] = typer.Option(None, "--api-key"),
):
    """Connect a platform."""

    async def _inner():
        settings = Settings(gie_env="local", require_auth=False)
        c = await build_container(memory=True, settings=settings)
        creds = {"api_key": api_key} if api_key else {"api_key": "dev-key"}
        req = ConnectRequest(
            tenant_id=tenant,
            platform_id=PlatformId(platform),
            name=name,
            auth_method=AuthMethod(auth),
            credentials=creds,
        )
        conn = await c.connect.handle(req, actor="cli", correlation_id="cli")
        rprint(conn.model_dump(mode="json"))

    _run(_inner())


@app.command("sync")
def sync(connection_id: str, tenant: str = typer.Option("default", "--tenant")):
    """Sync a connection."""

    async def _inner():
        from uuid import UUID

        settings = Settings(gie_env="local", require_auth=False)
        c = await build_container(memory=True, settings=settings)
        # reconnect sample if empty — sync expects existing; print error otherwise
        req = SyncRequest(
            connection_id=UUID(connection_id),
            tenant_id=tenant,
            payload={"kind": "policy_bundle", "count": 1},
        )
        try:
            result = await c.sync.handle(req, actor="cli", correlation_id="cli")
            rprint(result.model_dump(mode="json"))
        except Exception as exc:
            rprint(f"[red]{exc}[/red]")
            raise typer.Exit(1)

    _run(_inner())


@app.command("token")
def token(
    tenant: str = typer.Option("default", "--tenant"),
    subject: str = typer.Option("cli-user", "--subject"),
    method: str = typer.Option("jwt", "--method"),
):
    """Issue an auth token."""

    async def _inner():
        settings = Settings(gie_env="local", require_auth=False)
        c = await build_container(memory=True, settings=settings)
        tok = await c.auth.handle(
            AuthTokenRequest(
                tenant_id=tenant,
                auth_method=AuthMethod(method),
                subject=subject,
                scopes=["gie.read"],
            ),
            actor="cli",
        )
        rprint(tok.model_dump(mode="json"))

    _run(_inner())


if __name__ == "__main__":
    app()
