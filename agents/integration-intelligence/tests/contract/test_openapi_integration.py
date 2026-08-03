from integration_intelligence.adapters.rest.app import create_app

def test_openapi_paths():
    app = create_app()
    paths = app.openapi()["paths"]
    assert "/integrations" in paths
    assert "/integrations/connect" in paths
    assert "/webhooks/{platform_id}" in paths
    assert "/auth/token" in paths
    assert "/audit" in paths
    assert "/v1/integrations" in paths
