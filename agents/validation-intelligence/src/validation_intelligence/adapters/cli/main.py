from __future__ import annotations
import asyncio
import json
from pathlib import Path
from uuid import uuid4
import typer
from rich import print as rprint
from gie_contracts.validation import ValidateRequest, ValidationInputBundle

app = typer.Typer(name="gie-validate", help="GIE Validation Intelligence CLI")


@app.command()
def validate(input_json: Path, out: Path = Path("validation-report.json")):
    asyncio.run(_validate(input_json, out))


async def _validate(input_json: Path, out: Path):
    from validation_intelligence.infrastructure.bootstrap import build_container

    raw = json.loads(input_json.read_text())
    bundle = ValidationInputBundle.model_validate(
        raw if "tenant_id" in raw else raw.get("bundle", raw)
    )
    c = await build_container(memory=True)
    report = await c.validate.handle(
        ValidateRequest(bundle=bundle), actor="cli", correlation_id=uuid4().hex
    )
    out.write_text(report.model_dump_json(indent=2))
    rprint(report.summary)


@app.command()
def version():
    from validation_intelligence.version import AGENT_NAME, AGENT_VERSION

    rprint(f"{AGENT_NAME} {AGENT_VERSION}")


if __name__ == "__main__":
    app()
