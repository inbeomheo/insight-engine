"""헬스 liveness / ready / 전역 5xx 메트릭."""
from unittest.mock import patch

from app import create_app


def test_health_is_liveness_and_ready_is_separate():
    app = create_app({"TESTING": True})
    client = app.test_client()
    health = client.get("/health")
    ready = client.get("/ready")
    assert health.status_code == 200
    assert health.get_json()["status"] == "healthy"
    assert ready.status_code in (200, 503)
    assert ready.get_json()["status"] in ("ready", "not_ready")
    assert "checks" in ready.get_json()


def test_5xx_increments_error_count():
    app = create_app({"TESTING": True})

    @app.route("/boom")
    def boom():
        return {"error": "x"}, 500

    with patch("routes.utility._state._get_redis", return_value=None):
        client = app.test_client()
        before = client.get("/health").get_json()["error_count"]
        client.get("/boom")
        after = client.get("/health").get_json()["error_count"]
    assert after >= before + 1
