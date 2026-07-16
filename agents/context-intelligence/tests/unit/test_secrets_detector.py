"""Unit tests for secrets detector fingerprinting."""

from __future__ import annotations

from context_intelligence.domain.secrets_detector import (
    fingerprint_secret,
    scan_text_for_secrets,
)


def test_fingerprint_is_stable():
    fp1 = fingerprint_secret("sk-test-secret", pepper="pepper")
    fp2 = fingerprint_secret("sk-test-secret", pepper="pepper")
    assert fp1 == fp2
    assert fp1.startswith("sha256:")


def test_fingerprint_differs_with_pepper():
    fp1 = fingerprint_secret("sk-test-secret", pepper="a")
    fp2 = fingerprint_secret("sk-test-secret", pepper="b")
    assert fp1 != fp2


def test_scan_does_not_include_raw_secret():
    text = "OPENAI_API_KEY=sk-test-fake-key-for-unit-test\n"
    findings = scan_text_for_secrets(text, location=".env", pepper="test-pepper")
    assert len(findings) == 1
    finding = findings[0]
    assert finding.kind == "openai_api_key"
    assert "sk-test" not in finding.fingerprint
    assert finding.fingerprint.startswith("sha256:")
    dumped = finding.model_dump_json()
    assert "sk-test-fake-key" not in dumped


def test_fingerprint_matches_expected_format():
    raw = "sk-test-fake-key-for-unit-test"
    fp = fingerprint_secret(raw, pepper="test-pepper")
    findings = scan_text_for_secrets(
        f"OPENAI_API_KEY={raw}\n", location=".env", pepper="test-pepper"
    )
    assert findings[0].fingerprint == fp
