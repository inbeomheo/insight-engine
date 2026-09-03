import pytest

from app import create_app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://app.example.com,https://frontend.example.com",
    )
    app = create_app({"TESTING": False, "RATELIMIT_ENABLED": False})
    return app.test_client()


def post_probe(client, origin: str):
    return client.post(
        "/__csrf_probe__",
        base_url="https://app.example.com",
        headers={"Origin": origin},
    )


def post_probe_with_referer(client, referer: str):
    return client.post(
        "/__csrf_probe__",
        base_url="https://app.example.com",
        headers={"Referer": referer},
    )


def test_csrf_rejects_lookalike_origin(client):
    response = post_probe(client, "https://app.example.com.evil.test")

    assert response.status_code == 403


def test_csrf_rejects_file_origin(client):
    response = post_probe(client, "file://")

    assert response.status_code == 403


def test_csrf_rejects_lookalike_referer(client):
    response = post_probe_with_referer(
        client,
        "https://app.example.com.evil.test/forged-form",
    )

    assert response.status_code == 403


def test_csrf_accepts_exact_host_referer(client):
    response = post_probe_with_referer(client, "https://app.example.com/form")

    assert response.status_code == 404


@pytest.mark.parametrize(
    "origin",
    ["https://app.example.com", "https://frontend.example.com"],
)
def test_csrf_accepts_exact_host_or_allowlisted_origin(client, origin):
    response = post_probe(client, origin)

    # The probe route does not exist; reaching normal routing proves CSRF accepted it.
    assert response.status_code == 404
