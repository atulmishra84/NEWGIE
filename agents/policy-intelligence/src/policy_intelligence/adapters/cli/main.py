from __future__ import annotations
import asyncio
import json
from pathlib import Path
from uuid import uuid4
import typer
from rich import print as rprint
from gie_contracts.policy import PolicyGenerateRequest, PolicyInputBundle, PolicyTarget

app = typer.Typer(name="gie-policy", help="GIE Policy Intelligence CLI")

@app.command()
def generate(input_json: Path, out_dir: Path = Path("./policy-out"), memory: bool = True):
    """Generate policies from an input bundle JSON file."""
    asyncio.run(_generate(input_json, out_dir, memory))

async def _generate(input_json: Path, out_dir: Path, memory: bool):
    from policy_intelligence.infrastructure.bootstrap import build_container
    raw = json.loads(input_json.read_text())
    bundle = PolicyInputBundle.model_validate(raw if "tenant_id" in raw else raw.get("bundle", raw))
    container = await build_container(memory=memory)
    decision = await container.generate.handle(PolicyGenerateRequest(bundle=bundle), actor="cli", correlation_id=uuid4().hex)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "decision.json").write_text(decision.model_dump_json(indent=2))
    for art in decision.artifacts:
        (out_dir / art.filename).write_text(art.content)
    rprint(f"[green]Wrote {len(decision.artifacts)} artifacts + decision.json to {out_dir}[/green]")
    rprint(decision.summary)

@app.command()
def version():
    from policy_intelligence.version import AGENT_NAME, AGENT_VERSION
    rprint(f"{AGENT_NAME} {AGENT_VERSION}")

if __name__ == "__main__":
    app()
