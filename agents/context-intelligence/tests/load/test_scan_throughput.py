"""Light load test for scan throughput."""

from __future__ import annotations

import time
from pathlib import Path

from context_intelligence.application.scan_service import scan_folder


def test_scan_throughput_under_budget(sample_project_path: Path):
    """Repeated scans of small fixture should stay under 5s total."""
    iterations = 5
    start = time.perf_counter()
    for _ in range(iterations):
        model = scan_folder(sample_project_path, tenant_id="load-test")
        assert model.provenance.confidence.score > 0
    elapsed = time.perf_counter() - start
    avg = elapsed / iterations
    assert avg < 1.0, f"average scan took {avg:.2f}s, expected <1s"
    assert elapsed < 5.0, f"{iterations} scans took {elapsed:.2f}s total"
