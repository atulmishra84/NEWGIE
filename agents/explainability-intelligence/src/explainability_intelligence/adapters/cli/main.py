from __future__ import annotations
import asyncio
import json
from pathlib import Path
from uuid import uuid4
import typer
from rich import print as rprint
from gie_contracts.explainability import ExplainRequest, ExplainabilityInputBundle

app = typer.Typer(name="gie-explain", help="GIE Explainability Intelligence CLI")

@app.command()
def explain(input_json: Path, out: Path = Path("explanation.json")):
    asyncio.run(_explain(input_json, out))

async def _explain(input_json: Path, out: Path):
    from explainability_intelligence.infrastructure.bootstrap import build_container
    raw = json.loads(input_json.read_text())
    bundle = ExplainabilityInputBundle.model_validate(raw if "tenant_id" in raw else raw.get("bundle", raw))
    c = await build_container(memory=True)
    report = await c.explain.handle(ExplainRequest(bundle=bundle), actor="cli", correlation_id=uuid4().hex)
    out.write_text(report.model_dump_json(indent=2))
    art_dir = out.parent / "explanation-artifacts"
    art_dir.mkdir(exist_ok=True)
    for a in report.artifacts:
        (art_dir / a.filename).write_text(a.content)
    rprint(report.summary)

@app.command()
def version():
    from explainability_intelligence.version import AGENT_NAME, AGENT_VERSION
    rprint(f"{AGENT_NAME} {AGENT_VERSION}")

if __name__ == "__main__":
    app()
