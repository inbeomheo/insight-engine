"""
/generate 응답의 source_url 필드 에코백 테스트
"""
from __future__ import annotations

import json
import time
from unittest.mock import patch, MagicMock

import pytest

from app import create_app


@pytest.fixture
def app():
    application = create_app()
    application.config['TESTING'] = True
    return application


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


ORIGIN = {'Origin': 'http://localhost:3000'}


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestSourceUrlEcho:
    """source_url 에코백 테스트 — _save_and_respond 직접 테스트."""

    @patch('routes.generation_helpers.ai_service')
    @patch('routes.generation_helpers.save_history')
    @patch('routes.generation_helpers._webhook')
    def test_response_includes_source_url(self, mock_wh, mock_save, mock_ai, _mock_supa, app):
        """_save_and_respond 응답에 source_url이 포함되어야 한다."""
        from flask import g
        from routes.generation_helpers import _save_and_respond

        test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcB'
        result = {'title': '제목', 'content': '콘텐츠', 'html': '<p>콘텐츠</p>',
                  'usage': {'input_tokens': 100, 'output_tokens': 200}}
        params = {'style': 'blog_seo', 'model': 'gemini/gemini-2.5-flash',
                  'modifiers': {'length': 'medium', 'writing_style': 'conversational'}}

        mock_ai.extract_seo_metadata.return_value = None
        mock_ai.extract_geo_metadata.return_value = None
        mock_ai.extract_faq_schema.return_value = None
        mock_ai.extract_cta.return_value = None

        # AICacheService mock
        cache_mock = MagicMock()
        with app.test_request_context():
            app.ai_cache = cache_mock
            g.user_id = None
            resp = _save_and_respond(
                result, '프롬프트', None, 'cache_key',
                'dQw4w9WgXcB', params, test_url, '테스트 영상',
                '원본 자막', 'api', [], time.time(),
            )

        data = json.loads(resp.data)
        assert data['source_url'] == test_url

    @patch('routes.generation_helpers.ai_service')
    @patch('routes.generation_helpers.save_history')
    @patch('routes.generation_helpers._webhook')
    def test_source_url_is_string(self, mock_wh, mock_save, mock_ai, _mock_supa, app):
        """source_url은 문자열이어야 한다."""
        from flask import g
        from routes.generation_helpers import _save_and_respond

        test_url = 'https://example.com/article'
        result = {'title': 't', 'content': 'c', 'html': '<p>c</p>', 'usage': {}}
        params = {'style': 'summary', 'model': 'gemini/gemini-2.5-flash',
                  'modifiers': {}}
        cache_mock = MagicMock()
        with app.test_request_context():
            app.ai_cache = cache_mock
            g.user_id = None
            resp = _save_and_respond(
                result, 'p', None, 'k', None, params, test_url, '제목',
                '자막', 'api', [], time.time(),
            )

        data = json.loads(resp.data)
        assert isinstance(data['source_url'], str)
        assert data['source_url'] == test_url

    @patch('routes.generation_helpers.ai_service')
    @patch('routes.generation_helpers.save_history')
    @patch('routes.generation_helpers._webhook')
    def test_source_url_none_when_no_url(self, mock_wh, mock_save, mock_ai, _mock_supa, app):
        """url이 None이면 source_url도 None이어야 한다."""
        from flask import g
        from routes.generation_helpers import _save_and_respond

        result = {'title': 't', 'content': 'c', 'html': '<p>c</p>', 'usage': {}}
        params = {'style': 'summary', 'model': 'gemini/gemini-2.5-flash',
                  'modifiers': {}}
        cache_mock = MagicMock()
        with app.test_request_context():
            app.ai_cache = cache_mock
            g.user_id = None
            resp = _save_and_respond(
                result, 'p', None, 'k', None, params, None, '제목',
                '자막', 'api', [], time.time(),
            )

        data = json.loads(resp.data)
        assert data['source_url'] is None

    def test_direct_content_no_source_url(self, _mock_supa, client):
        """직접 텍스트 입력 모드 응답에는 source_url이 없다."""
        with patch('routes.blog_routes.ai_service') as mock_ai:
            mock_ai.create_content.return_value = (
                {'title': '제목', 'content': '내용', 'html': '<p>내용</p>',
                 'usage': {'input_tokens': 10, 'output_tokens': 20}},
                '프롬프트'
            )
            resp = client.post('/generate',
                               headers={**ORIGIN, 'Content-Type': 'application/json'},
                               data=json.dumps({
                                   'content': '직접 입력한 충분히 긴 텍스트입니다. ' * 10,
                               }))
            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert 'source_url' not in data
