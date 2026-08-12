from __future__ import annotations
import asyncio
import json
from pathlib import Path
from uuid import uuid4
import typer
from rich import print as rprint
from gie_contracts.compliance import ComplianceAnalyzeRequest, ComplianceInputBundle

app = typer.Typer(name="gie-compliance", help="GIE Compliance Intelligence CLI")


@app.command()
def analyze(input_json: Path, out: Path = Path("compliance-report.json")):
    asyncio.run(_analyze(input_json, out))


async def _analyze(input_json: Path, out: Path):
    from compliance_intelligence.infrastructure.bootstrap import build_container

    raw = json.loads(input_json.read_text())
    bundle = ComplianceInputBundle.model_validate(
        raw if "application_id" in raw else raw.get("bundle", raw)
    )
    c = await build_container(memory=True)
    report = await c.analyze.handle(
        ComplianceAnalyzeRequest(bundle=bundle), actor="cli", correlation_id=uuid4().hex
    )
    out.write_text(report.model_dump_json(indent=2))
    rprint(report.summary)


@app.command("frameworks")
def frameworks_cmd():
    from compliance_intelligence.domain.catalog import list_frameworks

    rprint(list_frameworks())


@app.command()
def version():
    from compliance_intelligence.version import AGENT_NAME, AGENT_VERSION

    rprint(f"{AGENT_NAME} {AGENT_VERSION}")


if __name__ == "__main__":
    app()
