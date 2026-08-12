from __future__ import annotations
import asyncio
import json
from pathlib import Path
from uuid import uuid4
import typer
from rich import print as rprint
from gie_contracts.learning import LearnRequest, LearningInputBundle

app = typer.Typer(name="gie-learn", help="GIE Learning Intelligence CLI")


@app.command()
def learn(input_json: Path, out: Path = Path("learning-report.json")):
    asyncio.run(_learn(input_json, out))


async def _learn(input_json: Path, out: Path):
    from learning_intelligence.infrastructure.bootstrap import build_container

    raw = json.loads(input_json.read_text())
    bundle = LearningInputBundle.model_validate(
        raw if "tenant_id" in raw else raw.get("bundle", raw)
    )
    c = await build_container(memory=True)
    report = await c.learn.handle(
        LearnRequest(bundle=bundle), actor="cli", correlation_id=uuid4().hex
    )
    out.write_text(report.model_dump_json(indent=2))
    rprint(report.summary)


@app.command()
def version():
    from learning_intelligence.version import AGENT_NAME, AGENT_VERSION

    rprint(f"{AGENT_NAME} {AGENT_VERSION}")


if __name__ == "__main__":
    app()
