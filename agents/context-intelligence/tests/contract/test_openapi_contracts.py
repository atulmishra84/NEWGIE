"""Contract tests against OpenAPI specification."""

from __future__ import annotations

from pathlib import Path

import yaml
from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename


def test_openapi_spec_is_valid(openapi_spec_path: Path):
    spec, _ = read_from_filename(str(openapi_spec_path))
    validate(spec)


def test_openapi_defines_scan_and_model_paths(openapi_spec_path: Path):
    spec = yaml.safe_load(openapi_spec_path.read_text())
    paths = spec["paths"]
    assert "/v1/scans" in paths
    assert "/v1/scans/{scan_id}" in paths
    assert "/v1/context-models/{model_id}" in paths
    assert paths["/v1/scans"]["post"]["security"]


def test_openapi_context_model_schema_version(openapi_spec_path: Path):
    spec = yaml.safe_load(openapi_spec_path.read_text())
    schema_version = (
        spec["components"]["schemas"]["ContextModel"]["properties"]["schema_version"]
    )
    assert schema_version["const"] == "gie.context.v1"
