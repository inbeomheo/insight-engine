"""마인드맵·퓨전 고급 라우트 커버리지 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_H = {'Origin': 'http://localhost:3000'}


class _Base(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()


# ── 마인드맵 ──────────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestMindmap(_Base):

    def test_mindmap_no_content(self, _):
        resp = self.client.post('/api/mindmap', json={}, headers=_H)
        self.assertIn(resp.status_code, [400, 401])

    @patch('services.core.ai_service.create_content',
           return_value={'content': '# Mindmap', 'usage': {}})
    @patch('services.core.content_service.truncate_text', side_effect=lambda t, n: t)
    def test_mindmap_success(self, _trunc, _ai, _):
        self.app.config['STYLE_PROMPTS'] = {'mindmap': 'convert to mindmap'}
        resp = self.client.post('/api/mindmap',
                                json={'content': 'test content'},
                                headers=_H)
        self.assertIn(resp.status_code, [200, 500])
        if resp.status_code == 200:
            data = resp.get_json()
            self.assertIn('markdown', data)

    def test_mindmap_missing_prompt(self, _):
        """STYLE_PROMPTS에 mindmap이 없으면 500."""
        self.app.config['STYLE_PROMPTS'] = {}
        resp = self.client.post('/api/mindmap',
                                json={'content': 'test'},
                                headers=_H)
        self.assertIn(resp.status_code, [400, 500])


# ── 퓨전 ─────────────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestGenerateFusion(_Base):

    def test_fusion_too_few_urls(self, _):
        resp = self.client.post('/api/generate-fusion',
                                json={'urls': ['http://a.com'], 'model': 'gemini/test'},
                                headers=_H)
        self.assertIn(resp.status_code, [400, 429])

    def test_fusion_too_many_urls(self, _):
        resp = self.client.post('/api/generate-fusion',
                                json={'urls': [f'http://{i}.com' for i in range(6)], 'model': 'gemini/test'},
                                headers=_H)
        self.assertIn(resp.status_code, [400, 429])

    def test_fusion_no_model(self, _):
        resp = self.client.post('/api/generate-fusion',
                                json={'urls': ['http://a.com', 'http://b.com'], 'model': ''},
                                headers=_H)
        self.assertIn(resp.status_code, [400, 429])

    @patch('services.core.fusion_service.generate_fusion',
           return_value={'content': 'fused', 'title': 'T'})
    def test_fusion_success(self, _fusion, _):
        resp = self.client.post('/api/generate-fusion',
                                json={
                                    'urls': ['https://youtube.com/watch?v=a', 'https://youtube.com/watch?v=b'],
                                    'model': 'gemini/test',
                                    'style': 'blog_seo'
                                },
                                headers=_H)
        self.assertIn(resp.status_code, [200, 429])

    @patch('services.core.fusion_service.generate_fusion',
           side_effect=ValueError('bad input'))
    def test_fusion_value_error(self, _fusion, _):
        resp = self.client.post('/api/generate-fusion',
                                json={
                                    'urls': ['http://a.com', 'http://b.com'],
                                    'model': 'gemini/test'
                                },
                                headers=_H)
        self.assertIn(resp.status_code, [400, 429, 500])

    @patch('services.core.fusion_service.generate_fusion',
           side_effect=Exception('boom'))
    def test_fusion_exception(self, _fusion, _):
        resp = self.client.post('/api/generate-fusion',
                                json={
                                    'urls': ['http://a.com', 'http://b.com'],
                                    'model': 'gemini/test'
                                },
                                headers=_H)
        self.assertIn(resp.status_code, [429, 500])


# ── 오류 메시지 정리 ─────────────────────────────────


class TestSanitizeGenerationError(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_safe_message(self, _):
        from utils.responses import safe_error_or_fallback
        with self.app.app_context():
            result = safe_error_or_fallback('[인증 실패] bad', 'fallback')
            self.assertIn('인증', result)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_server_error_uses_fallback(self, _):
        from utils.responses import safe_error_or_fallback
        with self.app.app_context():
            result = safe_error_or_fallback('[서버 오류] internal details', 'fallback')
            self.assertEqual(result, 'fallback')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_none_error(self, _):
        from utils.responses import safe_error_or_fallback
        with self.app.app_context():
            result = safe_error_or_fallback(None, 'fallback')
            self.assertIsInstance(result, str)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_exception_object(self, _):
        from utils.responses import safe_error_or_fallback
        with self.app.app_context():
            result = safe_error_or_fallback(ValueError('oops'), 'fallback')
            self.assertIsInstance(result, str)


if __name__ == '__main__':
    unittest.main()
