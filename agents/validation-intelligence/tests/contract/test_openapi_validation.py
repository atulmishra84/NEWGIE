from validation_intelligence.adapters.rest.app import create_app


def test_openapi_paths():
    app = create_app()
    paths = app.openapi()["paths"]
    assert "/validate" in paths
    assert "/v1/validate" in paths
    assert "/simulate" in paths
    assert "/validation/report" in paths
    assert "/validation/{validation_id}" in paths
