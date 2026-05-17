"""Application status payload service tests."""

from services.ops.status_service import build_home_status_payload


def test_build_home_status_payload_returns_public_api_status():
    assert build_home_status_payload() == {
        "status": "ok",
        "message": "Insight Engine API Server",
    }
