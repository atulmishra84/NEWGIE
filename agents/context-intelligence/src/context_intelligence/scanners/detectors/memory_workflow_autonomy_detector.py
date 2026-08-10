"""Memory stores, workflows, and autonomous agent detection."""

from __future__ import annotations

from pathlib import Path

from context_intelligence.domain.findings import FindingCategory, FindingSection
from context_intelligence.scanners.detectors.base import (
    BaseDetector,
    iter_files,
    read_text,
)
from context_intelligence.scanners.registry import DEFAULT_DETECTOR_REGISTRY

MEMORY_SIGNALS = [
    "memory",
    "ConversationBufferMemory",
    "RedisChatMessageHistory",
    "checkpointer",
]
WORKFLOW_SIGNALS = [
    "StateGraph",
    "langgraph.graph",
    "workflow",
    "DAG",
    "RunnableSequence",
]
AUTONOMY_SIGNALS = [
    "autonomous",
    "AutoGen",
    "Crew(",
    "AgentExecutor",
    "ReAct",
    "plan-and-execute",
]


@DEFAULT_DETECTOR_REGISTRY.register_detector()
class MemoryWorkflowAutonomyDetector(BaseDetector):
    detector_id = "memory_workflow_autonomy.detector.v1"
    section = FindingSection.AI
    default_category = FindingCategory.MEMORY

    async def detect(self, workspace_path: Path) -> list:
        findings = []

        for path in iter_files(
            workspace_path, extensions={".py", ".ts", ".js", ".yaml", ".yml"}
        ):
            text = read_text(path)
            if not text:
                continue
            lowered = text.lower()

            if any(sig.lower() in lowered for sig in MEMORY_SIGNALS):
                findings.append(
                    self.finding(
                        category=FindingCategory.MEMORY,
                        name=_first_match(text, MEMORY_SIGNALS) or "memory-store",
                        confidence=0.82,
                        rationale="Memory architecture reference",
                        path=str(path),
                    )
                )

            if any(sig.lower() in lowered for sig in WORKFLOW_SIGNALS):
                findings.append(
                    self.finding(
                        category=FindingCategory.WORKFLOW,
                        name=_first_match(text, WORKFLOW_SIGNALS) or "workflow",
                        confidence=0.85,
                        rationale="Workflow or graph orchestration",
                        path=str(path),
                    )
                )

            if any(sig.lower() in lowered for sig in AUTONOMY_SIGNALS):
                findings.append(
                    self.finding(
                        category=FindingCategory.AUTONOMOUS,
                        name=_first_match(text, AUTONOMY_SIGNALS) or "autonomous-agent",
                        confidence=0.8,
                        rationale="Autonomous agent capability",
                        path=str(path),
                    )
                )
        return findings


def _first_match(text: str, signals: list[str]) -> str | None:
    lowered = text.lower()
    for sig in signals:
        if sig.lower() in lowered:
            return sig
    return None
