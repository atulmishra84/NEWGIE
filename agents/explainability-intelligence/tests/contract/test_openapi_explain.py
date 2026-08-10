from explainability_intelligence.adapters.rest.app import create_app


def test_openapi_paths():
    app = create_app()
    paths = app.openapi()["paths"]
    assert "/explain" in paths
    assert "/v1/explain" in paths
    assert "/explanation/{explanation_id}" in paths
    assert "/reasoning/path" in paths
    assert "/figma-generate-diagram" in paths
