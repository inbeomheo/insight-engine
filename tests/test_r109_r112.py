"""R109~R111 autoresearch 테스트

R109: /api/mindmap 응답에 usage 필드 포함
R111: analytics_routes에서 int() → clamp_query_int 안전 변환
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


if __name__ == '__main__':
    unittest.main()
