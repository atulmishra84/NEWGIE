from gie_contracts.compliance import ControlStatus, FrameworkId
from compliance_intelligence.domain.catalog import list_frameworks, load_catalog
from compliance_intelligence.domain.engine import (
    analyze_compliance,
    determine_applicability,
)


def test_catalog_has_all_frameworks():
    cat = load_catalog()
    expected = {
        "hipaa",
        "gdpr",
        "pci_dss",
        "soc2",
        "iso27001",
        "nist_ai_rmf",
        "nist_csf",
        "eu_ai_act",
        "fda",
        "rbi",
        "mas",
        "dora",
        "ccpa",
        "internal_corporate",
    }
    assert expected.issubset(set(cat["frameworks"]))
    assert len(list_frameworks()) == 14


def test_applicability_and_gaps(sample_bundle):
    apps = determine_applicability(sample_bundle)
    applicable = {a.framework for a in apps if a.applicable}
    assert FrameworkId.HIPAA in applicable
    assert FrameworkId.GDPR in applicable
    assert FrameworkId.NIST_AI_RMF in applicable
    assert FrameworkId.INTERNAL in applicable
    report = analyze_compliance(sample_bundle)
    assert 0 <= report.compliance_score <= 1
    assert report.matrix
    assert report.gaps
    assert report.audit_package.get("package_id")
    assert report.control_mappings
    assert any(
        a.control_id == "hipaa-access" and a.status == ControlStatus.PARTIAL
        for a in report.assessments
    )
    assert report.summary
