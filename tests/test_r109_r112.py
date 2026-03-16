"""R109~R112 autoresearch 테스트

R109: /api/mindmap 응답에 usage 필드 포함
R110: /api/rewrite 응답에 elapsed_time 포함
R111: analytics_routes에서 int() → clamp_query_int 안전 변환
R112: /api/generate-multilang 응답에 language_count, succeeded, failed 포함
"""
import json
import unittest
from unittest.mock import patch, MagicMock

from app import create_app
from utils.responses import clamp_query_int


class TestR109MindmapUsage(unittest.TestCase):
    """R109: /api/mindmap 응답에 usage 필드가 포함되는지 검증"""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['STYLE_PROMPTS'] = {'mindmap': 'Convert to mindmap'}
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.ai_service.create_content')
    def test_mindmap_includes_usage(self, mock_create, mock_sb):
        mock_create.return_value = {
            'content': '# Mindmap\n- Topic A\n  - Sub A1',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
        }
        with self.app.test_request_context():
            resp = self.client.post('/api/mindmap',
                                   json={'content': 'Test content', 'model': 'gemini/gemini-2.5-flash'},
                                   headers={'X-User-Id': 'test-user'})
        data = resp.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('usage', data)
        self.assertEqual(data['usage']['total_tokens'], 150)
        self.assertIn('elapsed_time', data)


class TestR110RewriteElapsedTime(unittest.TestCase):
    """R110: /api/rewrite 응답에 elapsed_time이 포함되는지 검증"""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.content.rewrite_service.rewrite_for_platform')
    def test_rewrite_includes_elapsed_time(self, mock_rewrite, mock_sb):
        mock_rewrite.return_value = {
            'content': 'Rewritten for Twitter',
            'platform': 'twitter',
            'char_count': 42,
        }
        resp = self.client.post('/api/rewrite',
                                json={'content': 'Original content', 'platform': 'twitter',
                                      'model': 'gemini/gemini-2.5-flash'},
                                headers={'X-User-Id': 'test-user'})
        data = resp.get_json()
        self.assertIn('elapsed_time', data)
        self.assertIsInstance(data['elapsed_time'], float)
        self.assertGreaterEqual(data['elapsed_time'], 0)


class TestR111ClampQueryInt(unittest.TestCase):
    """R111: clamp_query_int가 잘못된 입력에 ValueError 없이 기본값 반환하는지 검증"""

    def test_valid_int(self):
        self.assertEqual(clamp_query_int('30', default=10, min_val=1, max_val=365), 30)

    def test_none_returns_default(self):
        self.assertEqual(clamp_query_int(None, default=30, min_val=1, max_val=365), 30)

    def test_invalid_string_returns_default(self):
        """int('abc')는 ValueError이지만 clamp_query_int는 기본값 반환"""
        self.assertEqual(clamp_query_int('abc', default=30, min_val=1, max_val=365), 30)

    def test_empty_string_returns_default(self):
        self.assertEqual(clamp_query_int('', default=30, min_val=1, max_val=365), 30)

    def test_below_min_clamped(self):
        self.assertEqual(clamp_query_int('-5', default=30, min_val=1, max_val=365), 1)

    def test_above_max_clamped(self):
        self.assertEqual(clamp_query_int('9999', default=30, min_val=1, max_val=365), 365)

    def test_float_string_returns_default(self):
        """float 형식 문자열도 안전하게 기본값 반환"""
        self.assertEqual(clamp_query_int('3.5', default=30, min_val=1, max_val=365), 30)


class TestR112MultilangCounts(unittest.TestCase):
    """R112: /api/generate-multilang 응답에 language_count, succeeded, failed 필드 포함"""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['STYLE_PROMPTS'] = {'blog_seo': 'Write SEO blog'}
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.advanced_routes._fetch_youtube_content')
    @patch('services.core.content_service.is_youtube_url', return_value=True)
    @patch('services.core.content_service.get_video_id', return_value='test123')
    @patch('services.core.content_service.get_content_title', return_value='Test Video')
    @patch('services.core.content_service.truncate_text', side_effect=lambda t, m: t)
    @patch('services.core.ai_service.create_content')
    def test_multilang_includes_counts(self, mock_create, mock_trunc, mock_title,
                                        mock_vid, mock_yt, mock_fetch, mock_sb):
        mock_fetch.return_value = ('transcript text', [], None, 'transcript text', 'api', [])
        mock_create.return_value = {
            'content': 'Generated content',
            'html': '<p>Generated</p>',
            'usage': {'prompt_tokens': 50, 'completion_tokens': 30, 'total_tokens': 80},
        }
        resp = self.client.post('/api/generate-multilang',
                                json={'url': 'https://youtube.com/watch?v=test123',
                                      'model': 'gemini/gemini-2.5-flash',
                                      'languages': ['ko', 'en']},
                                headers={'X-User-Id': 'test-user'})
        data = resp.get_json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data['language_count'], 2)
        self.assertEqual(data['succeeded'], 2)
        self.assertEqual(data['failed'], 0)
        self.assertIn('elapsed_time', data)


if __name__ == '__main__':
    unittest.main()
