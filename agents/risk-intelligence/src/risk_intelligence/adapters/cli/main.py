from __future__ import annotations
import asyncio
import json
from pathlib import Path
from uuid import uuid4
import typer
from rich import print as rprint
from gie_contracts.risk import RiskCalculateRequest, RiskInputBundle

app = typer.Typer(name="gie-risk", help="GIE Risk Intelligence CLI")

@app.command()
def calculate(input_json: Path, out: Path = Path("risk-report.json")):
    asyncio.run(_calc(input_json, out))

async def _calc(input_json: Path, out: Path):
    from risk_intelligence.infrastructure.bootstrap import build_container
    raw = json.loads(input_json.read_text())
    bundle = RiskInputBundle.model_validate(raw if "agent_id" in raw else raw.get("bundle", raw))
    c = await build_container(memory=True)
    report = await c.calculate.handle(RiskCalculateRequest(bundle=bundle), actor="cli", correlation_id=uuid4().hex)
    out.write_text(report.model_dump_json(indent=2))
    rprint(f"overall={report.overall_ai_risk_score} trust={report.trust_score} severity={report.severity.value}")
    rprint(f"wrote {out}")

@app.command()
def version():
    from risk_intelligence.version import AGENT_NAME, AGENT_VERSION
    rprint(f"{AGENT_NAME} {AGENT_VERSION}")

if __name__ == "__main__":
    app()
