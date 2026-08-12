"""Framework mappings: MITRE ATLAS, OWASP LLM Top 10, NIST AI RMF."""

from __future__ import annotations
from gie_contracts.risk import FrameworkMapping, RiskCategory

# category -> list of (framework, id, title)
CATEGORY_MAPPINGS: dict[RiskCategory, list[tuple[str, str, str]]] = {
    RiskCategory.PROMPT_INJECTION: [
        ("owasp_llm", "LLM01", "Prompt Injection"),
        ("mitre_atlas", "AML.T0051", "LLM Prompt Injection"),
        ("nist_ai_rmf", "MAP", "Map AI risks in context"),
    ],
    RiskCategory.JAILBREAK: [
        ("owasp_llm", "LLM01", "Prompt Injection"),
        ("mitre_atlas", "AML.T0054", "LLM Jailbreak"),
        ("nist_ai_rmf", "MEASURE", "Measure adversarial robustness"),
    ],
    RiskCategory.DATA_LEAKAGE: [
        ("owasp_llm", "LLM06", "Sensitive Information Disclosure"),
        ("mitre_atlas", "AML.T0048", "Exfiltration via ML Inference API"),
        ("nist_ai_rmf", "MANAGE", "Manage residual risk"),
    ],
    RiskCategory.TOOL_ABUSE: [
        ("owasp_llm", "LLM07", "Insecure Plugin Design"),
        ("owasp_llm", "LLM08", "Excessive Agency"),
        ("mitre_atlas", "AML.T0051", "LLM Prompt Injection"),
        ("nist_ai_rmf", "GOVERN", "Govern AI agency and tools"),
    ],
    RiskCategory.AUTONOMY: [
        ("owasp_llm", "LLM08", "Excessive Agency"),
        ("nist_ai_rmf", "GOVERN", "Human oversight and accountability"),
    ],
    RiskCategory.SUPPLY_CHAIN: [
        ("owasp_llm", "LLM05", "Supply Chain Vulnerabilities"),
        ("mitre_atlas", "AML.T0010", "ML Supply Chain Compromise"),
        ("nist_ai_rmf", "GOVERN", "Third-party AI risk"),
    ],
    RiskCategory.MODEL: [
        ("owasp_llm", "LLM10", "Model Theft"),
        ("owasp_llm", "LLM03", "Training Data Poisoning"),
        ("nist_ai_rmf", "MEASURE", "Model risk measurement"),
    ],
    RiskCategory.HALLUCINATION: [
        ("owasp_llm", "LLM09", "Overreliance"),
        ("nist_ai_rmf", "MEASURE", "Validity and reliability"),
    ],
    RiskCategory.PRIVACY: [
        ("owasp_llm", "LLM06", "Sensitive Information Disclosure"),
        ("nist_ai_rmf", "MAP", "Privacy risk contextualization"),
    ],
    RiskCategory.COMPLIANCE: [
        ("nist_ai_rmf", "GOVERN", "Compliance and policy alignment"),
    ],
    RiskCategory.IDENTITY: [
        ("nist_ai_rmf", "GOVERN", "Access control and identity"),
        ("owasp_llm", "LLM07", "Insecure Plugin Design"),
    ],
    RiskCategory.SECURITY: [
        ("owasp_llm", "LLM02", "Insecure Output Handling"),
        ("nist_ai_rmf", "MANAGE", "Security risk response"),
    ],
    RiskCategory.RUNTIME: [
        ("owasp_llm", "LLM04", "Model Denial of Service"),
        ("nist_ai_rmf", "MANAGE", "Runtime monitoring"),
    ],
    RiskCategory.SHADOW_AI: [
        ("nist_ai_rmf", "GOVERN", "Unsanctioned AI usage"),
        ("owasp_llm", "LLM05", "Supply Chain Vulnerabilities"),
    ],
    RiskCategory.BUSINESS: [
        ("nist_ai_rmf", "MAP", "Business context and impact"),
    ],
    RiskCategory.OPERATIONAL: [
        ("nist_ai_rmf", "MANAGE", "Operational resilience"),
        ("owasp_llm", "LLM04", "Model Denial of Service"),
    ],
}


def mappings_for(category: RiskCategory) -> list[FrameworkMapping]:
    rows = CATEGORY_MAPPINGS.get(category, [])
    by_fw: dict[str, FrameworkMapping] = {}
    for fw, sid, title in rows:
        m = by_fw.setdefault(fw, FrameworkMapping(framework=fw, ids=[], titles=[]))
        m.ids.append(sid)
        m.titles.append(title)
    return list(by_fw.values())
