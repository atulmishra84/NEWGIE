"""Prometheus-compatible metrics helpers."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

SCAN_REQUESTS = Counter(
    "gie_context_scan_requests_total",
    "Total scan requests",
    ["tenant_id", "source_type", "status"],
)
SCAN_DURATION = Histogram(
    "gie_context_scan_duration_seconds",
    "Scan duration in seconds",
    ["source_type"],
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300),
)
MODEL_GETS = Counter(
    "gie_context_model_gets_total",
    "Context model GET requests",
    ["cache_hit"],
)
ACTIVE_SCANS = Gauge(
    "gie_context_active_scans",
    "Currently running scans",
)
DETECTOR_RUNS = Counter(
    "gie_context_detector_runs_total",
    "Detector executions",
    ["detector_id", "status"],
)
PIPELINE_STAGE_DURATION = Histogram(
    "gie_context_pipeline_stage_duration_seconds",
    "Pipeline stage duration in seconds",
    ["stage"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120),
)

__all__ = [
    "ACTIVE_SCANS",
    "DETECTOR_RUNS",
    "MODEL_GETS",
    "PIPELINE_STAGE_DURATION",
    "SCAN_DURATION",
    "SCAN_REQUESTS",
]
