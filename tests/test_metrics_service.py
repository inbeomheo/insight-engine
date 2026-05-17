"""Prometheus metrics rendering service tests."""

from services.ops.metrics_service import build_prometheus_metrics


def test_build_prometheus_metrics_includes_core_and_queue_metrics():
    body = build_prometheus_metrics(
        total_requests=10,
        total_errors=2,
        error_rate=0.2,
        active_requests=3,
        queue_summary={"queued": 1, "publishing": 2, "success": 3, "failed": 4, "total": 10},
        memory_rss_bytes=4096,
        python_version="3.13",
    )

    assert "insight_requests_total 10" in body
    assert "insight_errors_total 2" in body
    assert "insight_error_rate 0.2" in body
    assert "insight_active_requests 3" in body
    assert 'insight_publish_queue_items{status="queued"} 1' in body
    assert 'insight_publish_queue_total 10' in body
    assert "insight_memory_rss_bytes 4096" in body
    assert 'insight_build_info{python_version="3.13"} 1' in body
    assert body.endswith("\n")


def test_build_prometheus_metrics_omits_queue_metrics_when_unavailable():
    body = build_prometheus_metrics(
        total_requests=0,
        total_errors=0,
        error_rate=0.0,
        active_requests=0,
        queue_summary={},
        memory_rss_bytes=None,
        python_version="3.13",
    )

    assert "insight_publish_queue_items" not in body
    assert "insight_memory_rss_bytes" not in body
