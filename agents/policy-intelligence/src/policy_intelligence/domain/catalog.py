"""Built-in guardrail catalog mapped to knowledge/risk/compliance signals."""

from __future__ import annotations
from dataclasses import dataclass
from gie_contracts.policy import BusinessImpact, Effort, Priority


@dataclass(frozen=True)
class GuardrailSpec:
    guardrail_id: str
    name: str
    category: str
    triggers: tuple[str, ...]  # keywords in context/risk/compliance/knowledge
    priority: Priority
    business_impact: BusinessImpact
    effort: Effort
    controls: tuple[str, ...]
    knowledge_ids: tuple[str, ...]
    why_template: str


CATALOG: list[GuardrailSpec] = [
    GuardrailSpec(
        "gr-prompt-injection",
        "Prompt Injection Defense",
        "input_security",
        (
            "prompt injection",
            "llm01",
            "jailbreak",
            "langgraph",
            "crewai",
            "autogen",
            "openai",
            "agents",
        ),
        Priority.P0,
        BusinessImpact.CRITICAL,
        Effort.MEDIUM,
        ("input_filter", "instruction_hierarchy", "untrusted_content_isolation"),
        ("owasp-llm01", "gr-input-filter", "pi-direct"),
        "Detected AI agent/framework surface with prompt-injection exposure ({signals}).",
    ),
    GuardrailSpec(
        "gr-output-filter",
        "Output Content Filtering",
        "output_security",
        (
            "sensitive",
            "pii",
            "secret",
            "llm06",
            "disclosure",
            "healthcare",
            "hipaa",
            "pci",
        ),
        Priority.P0,
        BusinessImpact.CRITICAL,
        Effort.MEDIUM,
        ("output_filter", "dlp_scan", "secret_redaction"),
        ("owasp-llm06", "gr-output-filter", "hipaa-phi-min"),
        "Sensitive data or regulated workload signals require output filtering ({signals}).",
    ),
    GuardrailSpec(
        "gr-tool-allowlist",
        "Tool / Function Allowlist",
        "agency_control",
        (
            "tool",
            "mcp",
            "plugin",
            "function calling",
            "llm07",
            "llm08",
            "excessive agency",
            "autonomous",
        ),
        Priority.P0,
        BusinessImpact.HIGH,
        Effort.MEDIUM,
        ("tool_allowlist", "schema_validation", "human_in_loop"),
        ("owasp-llm07", "owasp-llm08", "gr-tool-allowlist", "rt-no-shell"),
        "Tools/MCP/plugins or autonomy signals require allowlisting and privilege limits ({signals}).",
    ),
    GuardrailSpec(
        "gr-pii-presidio",
        "PII Detection & Anonymization",
        "privacy",
        ("pii", "presidio", "gdpr", "hipaa", "personal data", "phi", "healthcare"),
        Priority.P1,
        BusinessImpact.HIGH,
        Effort.LOW,
        ("presidio_analyze", "presidio_anonymize"),
        ("gdpr-art32", "hipaa-phi-min", "gr-output-filter"),
        "PII/PHI or privacy frameworks detected ({signals}).",
    ),
    GuardrailSpec(
        "gr-rate-limit",
        "Rate & Cost Controls",
        "availability",
        ("dos", "llm04", "cost", "token", "rate"),
        Priority.P1,
        BusinessImpact.MEDIUM,
        Effort.LOW,
        ("rate_limit", "token_budget"),
        ("owasp-llm04", "gr-rate-limit", "rt-max-tokens"),
        "Availability/cost risk signals require throttling ({signals}).",
    ),
    GuardrailSpec(
        "gr-identity-rbac",
        "Agent Identity & RBAC",
        "identity",
        ("identity", "rbac", "oauth", "entra", "auth0", "workload identity", "api key"),
        Priority.P1,
        BusinessImpact.HIGH,
        Effort.MEDIUM,
        ("agent_rbac", "short_lived_tokens", "least_privilege"),
        ("id-least-privilege", "pol-agent-rbac", "soc2-cc6"),
        "Identity/auth surfaces require least-privilege agent RBAC ({signals}).",
    ),
    GuardrailSpec(
        "gr-topic-safety",
        "Topic & Safety Blocklist",
        "safety",
        ("moderation", "safety", "content filter", "nemo", "foundry", "openai"),
        Priority.P2,
        BusinessImpact.MEDIUM,
        Effort.LOW,
        ("topic_blocklist", "toxicity_filter"),
        ("gr-topic-block", "vendor-openai", "vendor-azure-ai"),
        "Model platform usage benefits from native safety/topic controls ({signals}).",
    ),
    GuardrailSpec(
        "gr-opa-runtime",
        "OPA Runtime Admission Policies",
        "runtime_policy",
        ("kubernetes", "opa", "rego", "deployment", "runtime", "egress"),
        Priority.P1,
        BusinessImpact.HIGH,
        Effort.HIGH,
        ("opa_admission", "egress_allowlist", "deny_shell"),
        ("rt-net-egress", "rt-no-shell", "iso-a5"),
        "Runtime/K8s deployment signals warrant OPA/Rego admission controls ({signals}).",
    ),
    GuardrailSpec(
        "gr-nemo-rails",
        "NVIDIA NeMo Guardrails",
        "vendor_rail",
        ("nemo", "nvidia", "colang", "rails"),
        Priority.P2,
        BusinessImpact.MEDIUM,
        Effort.MEDIUM,
        ("nemo_input_rails", "nemo_output_rails", "nemo_dialog_rails"),
        ("gr-input-filter", "gr-output-filter"),
        "NeMo/NVIDIA stack detected — emit Colang/rails configuration ({signals}).",
    ),
    GuardrailSpec(
        "gr-eu-ai-transparency",
        "EU AI Act Transparency",
        "compliance",
        ("eu ai act", "high-risk", "transparency", "euai"),
        Priority.P1,
        BusinessImpact.HIGH,
        Effort.MEDIUM,
        ("ai_disclosure", "logging_retention", "human_oversight"),
        ("euai-high-risk", "euai-transparency", "nist-govern"),
        "EU AI Act / high-risk compliance signals require transparency controls ({signals}).",
    ),
]
