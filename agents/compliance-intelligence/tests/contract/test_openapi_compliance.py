from compliance_intelligence.adapters.rest.app import create_app

def test_openapi_has_compliance_paths():
    app = create_app()
    paths = app.openapi()["paths"]
    assert "/v1/compliance/analyze" in paths
    assert "/compliance/analyze" in paths
    assert "/v1/compliance/validate" in paths
    assert "/compliance/report" in paths
    assert "/compliance/evidence" in paths
    assert "/frameworks" in paths
