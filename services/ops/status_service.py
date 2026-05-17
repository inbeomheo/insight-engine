"""Simple application status payload helpers."""


def build_home_status_payload() -> dict[str, str]:
    """Build the root API status response payload."""
    return {
        "status": "ok",
        "message": "Insight Engine API Server",
    }
