from knowledge_intelligence.adapters.rest.app import create_app


def test_openapi_has_knowledge_paths():
    app = create_app()
    schema = app.openapi()
    paths = schema["paths"]
    assert "/v1/knowledge/query" in paths
    assert "/v1/knowledge/nodes" in paths
    assert "/health" in paths
