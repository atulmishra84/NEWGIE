from __future__ import annotations
import asyncio
import json
from pathlib import Path
from uuid import uuid4
import typer
from rich import print as rprint
from gie_contracts.recommendation import RecommendationGenerateRequest, RecommendationInputBundle

app = typer.Typer(name="gie-recommend", help="GIE Recommendation Intelligence CLI")

@app.command()
def generate(input_json: Path, out: Path = Path("recommendations.json")):
    asyncio.run(_generate(input_json, out))

async def _generate(input_json: Path, out: Path):
    from recommendation_intelligence.infrastructure.bootstrap import build_container
    raw = json.loads(input_json.read_text())
    bundle = RecommendationInputBundle.model_validate(raw if "agent_id" in raw else raw.get("bundle", raw))
    c = await build_container(memory=True)
    report = await c.generate.handle(RecommendationGenerateRequest(bundle=bundle), actor="cli", correlation_id=uuid4().hex)
    out.write_text(report.model_dump_json(indent=2))
    rprint(report.summary)

@app.command()
def version():
    from recommendation_intelligence.version import AGENT_NAME, AGENT_VERSION
    rprint(f"{AGENT_NAME} {AGENT_VERSION}")

if __name__ == "__main__":
    app()
