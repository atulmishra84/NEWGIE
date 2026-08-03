from policy_intelligence.adapters.rest.app import create_app


def test_openapi_paths():
    app = create_app()
    paths = app.openapi()["paths"]
    assert "/v1/policies/generate" in paths
    assert "/health" in paths
