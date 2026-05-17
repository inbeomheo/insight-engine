"""Prometheus metrics rendering helpers."""


def build_prometheus_metrics(
    *,
    total_requests: int,
    total_errors: int,
    error_rate: float,
    active_requests: int,
    queue_summary: dict,
    memory_rss_bytes: int | None,
    python_version: str,
) -> str:
    """Build Prometheus text exposition format for application metrics."""
    lines = [
        '# HELP insight_requests_total HTTP requests total',
        '# TYPE insight_requests_total counter',
        f'insight_requests_total {total_requests}',
        '# HELP insight_errors_total 5xx responses total',
        '# TYPE insight_errors_total counter',
        f'insight_errors_total {total_errors}',
        '# HELP insight_error_rate cumulative error rate (0.0-1.0)',
        '# TYPE insight_error_rate gauge',
        f'insight_error_rate {error_rate}',
        '# HELP insight_active_requests currently active requests',
        '# TYPE insight_active_requests gauge',
        f'insight_active_requests {active_requests}',
    ]

    if queue_summary:
        lines.append('# HELP insight_publish_queue_items publish queue items by status')
        lines.append('# TYPE insight_publish_queue_items gauge')
        for status in ('queued', 'publishing', 'success', 'failed'):
            count = queue_summary.get(status, 0)
            lines.append(f'insight_publish_queue_items{{status="{status}"}} {count}')
        lines.append(f'insight_publish_queue_total {queue_summary.get("total", 0)}')

    if memory_rss_bytes is not None:
        lines.append('# HELP insight_memory_rss_bytes process RSS memory usage in bytes')
        lines.append('# TYPE insight_memory_rss_bytes gauge')
        lines.append(f'insight_memory_rss_bytes {memory_rss_bytes}')

    lines.append('# HELP insight_build_info build information')
    lines.append('# TYPE insight_build_info gauge')
    lines.append(f'insight_build_info{{python_version="{python_version}"}} 1')

    return '\n'.join(lines) + '\n'
