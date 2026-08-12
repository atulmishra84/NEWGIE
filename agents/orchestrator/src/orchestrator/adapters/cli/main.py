from __future__ import annotations
import asyncio
import json
import typer
from rich import print as rprint
from gie_contracts.orchestrator import AnalyzeRequest, ExecutionMode
from orchestrator.infrastructure.bootstrap import build_container
from orchestrator.settings import Settings
from orchestrator.domain.graph import (
    default_analyze_workflow,
    mermaid_execution_graph,
    topological_waves,
)

app = typer.Typer(name="gie-orchestrate", help="GIE Orchestrator CLI")


def _run(coro):
    return asyncio.run(coro)


@app.command("analyze")
def analyze(
    tenant: str = typer.Option("default", "--tenant"),
    source: str = typer.Option(".", "--source"),
    mode: str = typer.Option("sync", "--mode"),
    sequential: bool = typer.Option(False, "--sequential"),
):
    """Run unified analysis."""

    async def _inner():
        settings = Settings(gie_env="local", require_auth=False, simulate_agents=True)
        c = await build_container(memory=True, settings=settings)
        req = AnalyzeRequest(
            tenant_id=tenant,
            source={"path": source},
            mode=ExecutionMode(mode),
            options={"sequential": sequential},
        )
        rec = await c.analyze.handle(req, actor="cli")
        rprint(json.dumps(rec.model_dump(mode="json"), indent=2, default=str))

    _run(_inner())


@app.command("graph")
def graph(parallel: bool = typer.Option(True, "--parallel/--sequential")):
    """Print execution graph (Mermaid) and waves."""
    wf = default_analyze_workflow(parallel_enabled=parallel)
    rprint(mermaid_execution_graph(wf))
    rprint("waves:", [[s.step_id for s in wave] for wave in topological_waves(wf)])


@app.command("status")
def status():
    async def _inner():
        settings = Settings(gie_env="local", require_auth=False, simulate_agents=True)
        await build_container(memory=True, settings=settings)
        from orchestrator.domain.router import default_health

        for a in default_health(settings):
            rprint(
                f"{a.agent_id.value}: {'ok' if a.healthy else 'down'} @ {a.base_url}"
            )

    _run(_inner())


if __name__ == "__main__":
    app()
