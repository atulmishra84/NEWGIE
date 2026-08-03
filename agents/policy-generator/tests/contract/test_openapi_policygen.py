from policy_generator.adapters.rest.app import create_app

def test_openapi_has_policy_paths():
    app = create_app()
    paths = app.openapi()["paths"]
    assert "/v1/policy/generate" in paths
    assert "/policy/generate" in paths
    assert "/policy/validate" in paths
    assert "/policy/templates" in paths
    assert "/policy/{policy_id}" in paths
