from learning_intelligence.adapters.rest.app import create_app


def test_openapi_paths():
    app = create_app()
    paths = app.openapi()["paths"]
    assert "/feedback" in paths
    assert "/learn" in paths
    assert "/learning/history" in paths
    assert "/knowledge/changes" in paths
    assert "/v1/feedback" in paths
