from orchestrator.adapters.rest.app import create_app

def test_openapi_paths():
    app = create_app()
    paths = app.openapi()["paths"]
    assert "/analyze" in paths
    assert "/workflow" in paths
    assert "/status" in paths
    assert "/execution/{execution_id}" in paths
    assert "/trace/{trace_id}" in paths
    assert "/v1/analyze" in paths
