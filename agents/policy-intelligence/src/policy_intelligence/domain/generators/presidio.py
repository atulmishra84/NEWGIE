from __future__ import annotations
from typing import Any
from gie_contracts.policy import GuardrailRecommendation, PolicyInputBundle

def render(recs: list[GuardrailRecommendation], bundle: PolicyInputBundle) -> dict[str, Any]:
    entities = ["CREDIT_CARD", "EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", "PERSON", "LOCATION", "IBAN_CODE"]
    if "hipaa" in str(bundle.compliance).lower() or "phi" in str(bundle.context).lower():
        entities += ["MEDICAL_LICENSE", "DATE_TIME"]
    return {
        "vendor": "microsoft_presidio",
        "version": "1.0",
        "controls": [{"id": c, "guardrail": r.guardrail_id} for r in recs for c in r.controls],
        "presidio": {
            "analyzer": {
                "language": "en",
                "entities": entities,
                "score_threshold": 0.5,
            },
            "anonymizer": {
                "default_operator": "replace",
                "operators": {
                    "CREDIT_CARD": {"type": "mask", "masking_char": "*", "chars_to_mask": 12, "from_end": True},
                    "EMAIL_ADDRESS": {"type": "replace", "new_value": "<EMAIL>"},
                    "PERSON": {"type": "replace", "new_value": "<PERSON>"},
                },
            },
            "apply_to": ["prompts", "completions", "tool_args", "logs"],
        },
        "rationale": [r.why[0] for r in recs if r.why],
    }
