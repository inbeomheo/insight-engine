"""Share page public URL behavior."""
from services.content.share_page_service import public_origin


def test_public_origin_prefers_explicit_public_origin(monkeypatch):
    monkeypatch.setenv('PUBLIC_ORIGIN', 'https://share.example.com/')
    monkeypatch.setenv('INSIGHT_BASE_URL', 'https://insight.example.com')
    monkeypatch.setenv('APP_BASE_URL', 'https://app.example.com')

    assert public_origin() == 'https://share.example.com'


def test_public_origin_falls_back_to_deployment_base_urls(monkeypatch):
    monkeypatch.delenv('PUBLIC_ORIGIN', raising=False)
    monkeypatch.setenv('INSIGHT_BASE_URL', 'https://insight.example.com/')
    monkeypatch.setenv('APP_BASE_URL', 'https://app.example.com/')

    assert public_origin() == 'https://insight.example.com'

    monkeypatch.delenv('INSIGHT_BASE_URL', raising=False)
    assert public_origin() == 'https://app.example.com'
