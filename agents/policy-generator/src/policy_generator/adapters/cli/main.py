from __future__ import annotations
import asyncio
import json
from pathlib import Path
from uuid import uuid4
import typer
from rich import print as rprint
from gie_contracts.policy_generator import (
    PolicyPackageGenerateRequest,
    PolicyGeneratorInputBundle,
)

app = typer.Typer(name="gie-policygen", help="GIE Policy Generator CLI")


@app.command()
def generate(input_json: Path, out: Path = Path("policy-package.json")):
    asyncio.run(_generate(input_json, out))


async def _generate(input_json: Path, out: Path):
    from policy_generator.infrastructure.bootstrap import build_container

    raw = json.loads(input_json.read_text())
    bundle = PolicyGeneratorInputBundle.model_validate(
        raw if "agent_id" in raw else raw.get("bundle", raw)
    )
    c = await build_container(memory=True)
    pkg = await c.generate.handle(
        PolicyPackageGenerateRequest(bundle=bundle),
        actor="cli",
        correlation_id=uuid4().hex,
    )
    out.write_text(pkg.model_dump_json(indent=2))
    # also write named artifacts beside out
    art_dir = out.with_suffix("").parent / "artifacts"
    art_dir.mkdir(exist_ok=True)
    for name, content in pkg.named_artifacts.items():
        (art_dir / name).write_text(content)
    rprint(pkg.summary)


@app.command("templates")
def templates_cmd():
    from policy_generator.domain.templates import list_templates

    for t in list_templates():
        rprint(f"{t.template_id}: {t.filename}")


@app.command()
def version():
    from policy_generator.version import AGENT_NAME, AGENT_VERSION

    rprint(f"{AGENT_NAME} {AGENT_VERSION}")


if __name__ == "__main__":
    app()
