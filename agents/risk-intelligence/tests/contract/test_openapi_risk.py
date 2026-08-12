from risk_intelligence.adapters.rest.app import create_app


def test_openapi_has_risk_paths():
    app = create_app()
    paths = app.openapi()["paths"]
    assert "/v1/risk/calculate" in paths
    assert "/risk/calculate" in paths
    assert "/v1/risk/history" in paths
    assert "/v1/risk/remediation" in paths
