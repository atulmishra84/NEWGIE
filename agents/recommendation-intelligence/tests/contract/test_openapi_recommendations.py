from recommendation_intelligence.adapters.rest.app import create_app

def test_openapi_has_recommendation_paths():
    app = create_app()
    paths = app.openapi()["paths"]
    assert "/v1/recommendations" in paths or "/v1/recommendations/" in paths
    assert "/recommendations/history" in paths
    assert "/recommendations/approve" in paths
    assert "/recommendations/{agent_id}" in paths
