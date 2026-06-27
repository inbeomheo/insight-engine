"""Costly app feature routes require authentication when app auth is enabled."""

import pytest

from app import create_app
from src.contexts.identity.interface import auth_decorators


def _client(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'development')
    monkeypatch.setattr(auth_decorators, 'is_supabase_enabled', lambda: True)
    app = create_app({'TESTING': True})
    return app.test_client()


@pytest.mark.parametrize(
    ('path', 'payload'),
    (
        ('/api/mcp-apps/example/render', {}),
        ('/api/mcp-apps/example/action', {'action': 'run'}),
        ('/api/providers/validate', {'provider_id': 'gemini', 'api_key': 'key'}),
        ('/api/feedback', {'style_id': 'blog_seo', 'content_id': 'c1', 'rating': 'like'}),
        ('/api/fact-check', {'content': 'content'}),
        ('/api/seo-optimize', {'content': 'content'}),
        ('/api/plagiarism-check', {'content': 'content'}),
        ('/api/readability', {'text': 'content'}),
        ('/api/sentiment-flow', {'content': 'content'}),
        ('/api/feedback/nps', {'score': 9}),
        ('/api/recommend-sources', {'topic': 'AI'}),
        ('/api/qa-check', {'content': 'content'}),
        ('/api/agent/chat', {'message': 'hello'}),
        ('/api/agent/chat/stream', {'message': 'hello'}),
        ('/api/agent/sdk', {'message': 'hello'}),
        ('/api/notebooklm/generate', {'type': 'brief', 'url': 'https://example.com', 'source_text': 'text'}),
        ('/api/extract-events', {'transcript': 'event text'}),
    ),
)
def test_costly_app_feature_routes_require_auth(monkeypatch, path, payload):
    client = _client(monkeypatch)

    response = client.post(
        path,
        json=payload,
        headers={'Origin': 'http://localhost:3000'},
    )

    assert response.status_code == 401
    assert response.get_json()['code'] == 'AUTH_REQUIRED'
