"""Readiness service tests."""

from services.ops.readiness_service import build_readiness_report


class _FakeRedisClient:
    def __init__(self, ping_error=None):
        self._ping_error = ping_error

    def ping(self):
        if self._ping_error:
            raise self._ping_error
        return True


def test_build_readiness_report_all_optional_dependencies_disabled():
    report = build_readiness_report(
        environ={"REDIS_URL": "", "RAG_ENABLED": "false", "RUN_SCHEDULER": "0"},
        is_supabase_enabled=lambda: False,
    )

    assert report.ready is True
    assert report.checks == {
        "redis": "skipped (REDIS_URL unset)",
        "supabase": "disabled",
        "chroma_db": "disabled",
    }


def test_build_readiness_report_fails_when_redis_ping_fails():
    report = build_readiness_report(
        environ={
            "REDIS_URL": "redis://example.test:6379/0",
            "RAG_ENABLED": "false",
            "RUN_SCHEDULER": "0",
        },
        redis_from_url=lambda *args, **kwargs: _FakeRedisClient(TimeoutError()),
        is_supabase_enabled=lambda: False,
    )

    assert report.ready is False
    assert report.checks["redis"] == "fail: TimeoutError"


def test_build_readiness_report_fails_when_rag_path_is_not_writable():
    report = build_readiness_report(
        environ={
            "REDIS_URL": "",
            "RAG_ENABLED": "true",
            "CHROMA_DB_PATH": "/data/chroma",
            "RUN_SCHEDULER": "0",
        },
        is_supabase_enabled=lambda: False,
        path_is_dir=lambda path: path == "/data/chroma",
        path_is_writable=lambda path: False,
    )

    assert report.ready is False
    assert report.checks["chroma_db"] == "fail: path not writable (/data/chroma)"


def test_build_readiness_report_fails_when_required_scheduler_is_stopped():
    report = build_readiness_report(
        environ={"REDIS_URL": "", "RAG_ENABLED": "false", "RUN_SCHEDULER": "true"},
        is_supabase_enabled=lambda: False,
        is_scheduler_running=lambda: False,
    )

    assert report.ready is False
    assert report.checks["scheduler"] == "stopped"


def test_build_readiness_report_keeps_supabase_import_failure_non_blocking():
    def broken_supabase_check():
        raise RuntimeError("boom")

    report = build_readiness_report(
        environ={"REDIS_URL": "", "RAG_ENABLED": "false", "RUN_SCHEDULER": "0"},
        is_supabase_enabled=broken_supabase_check,
    )

    assert report.ready is True
    assert report.checks["supabase"] == "fail: RuntimeError"
