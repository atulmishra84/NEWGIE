"""Unified Lambda dispatcher for all 15 GIE Bedrock Agent action groups.

Bedrock passes the actionGroup name in the event; we route to the appropriate
per-agent handler module without importing all of them at cold-start.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

from shared import err, parse_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Maps Bedrock action-group name → handler module name (relative to this package)
_ACTION_GROUP_MAP: dict[str, str] = {
    "ContextIntelligence":          "context_intelligence_handler",
    "KnowledgeIntelligence":        "knowledge_intelligence_handler",
    "RiskIntelligence":             "risk_intelligence_handler",
    "PolicyIntelligence":           "policy_intelligence_handler",
    "ComplianceIntelligence":       "compliance_intelligence_handler",
    "RecommendationIntelligence":   "recommendation_intelligence_handler",
    "ExplainabilityIntelligence":   "explainability_intelligence_handler",
    "ValidationIntelligence":       "validation_intelligence_handler",
    "LearningIntelligence":         "learning_intelligence_handler",
    "IntegrationIntelligence":      "integration_intelligence_handler",
    "PolicyGenerator":              "policy_generator_handler",
    "Orchestrator":                 "orchestrator_handler",
    "ChiefOrchestrator":            "chief_orchestrator_handler",
    "PolicyEngine":                 "policy_engine_handler",
    "RiskAssessment":               "risk_assessment_handler",
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ag, fn, _ = parse_event(event)
    logger.info("dispatcher: action_group=%s function=%s", ag, fn)

    module_name = _ACTION_GROUP_MAP.get(ag)
    if not module_name:
        logger.error("Unknown action group: %s", ag)
        return err(ag, fn, f"Unknown action group: {ag}. Valid groups: {list(_ACTION_GROUP_MAP)}")

    try:
        module = importlib.import_module(module_name)
        return module.lambda_handler(event, context)
    except ImportError as exc:
        logger.exception("Failed to import handler module %s", module_name)
        return err(ag, fn, f"Handler module not found: {module_name}: {exc}")
    except Exception as exc:
        logger.exception("Unhandled error in %s/%s", ag, fn)
        return err(ag, fn, str(exc))
