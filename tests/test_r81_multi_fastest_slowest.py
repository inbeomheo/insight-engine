"""R81: generate-multi 응답에 fastest_style, slowest_style 필드 추가 테스트"""
import unittest
from unittest.mock import patch, MagicMock
import time

from app import create_app


class TestMultiFastestSlowest(unittest.TestCase):
    """generate-multi 응답의 fastest/slowest 스타일 필드 검증"""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.ai_service.create_content')
    @patch('routes.advanced_routes._fetch_youtube_content')
    @patch('routes.advanced_routes.content_service')
    def test_fastest_slowest_present(self, mock_cs, mock_fetch, mock_create, mock_supa):
        """응답에 fastest_style, slowest_style 필드가 존재"""
        mock_cs.is_youtube_url.return_value = True
        mock_cs.get_video_id.return_value = 'test123'
        mock_cs.get_content_title.return_value = '테스트'
        mock_cs.truncate_text.side_effect = lambda t, m: t
        mock_fetch.return_value = ('자막', None, None, [], 'api', None)
        mock_create.return_value = {'title': '결과', 'content': '내용', 'html': '<p>내용</p>'}

        with self.app.app_context():
            self.app.config['STYLE_PROMPTS'] = {'summary': '요약', 'blog_seo': 'SEO'}

        resp = self.client.post('/api/generate-multi', json={
            'url': 'https://www.youtube.com/watch?v=test123',
            'styles': ['summary', 'blog_seo'],
        }, headers={'Origin': 'http://localhost:3000'})

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('fastest_style', data)
        self.assertIn('slowest_style', data)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.ai_service.create_content')
    @patch('routes.advanced_routes._fetch_youtube_content')
    @patch('routes.advanced_routes.content_service')
    def test_fastest_slowest_structure(self, mock_cs, mock_fetch, mock_create, mock_supa):
        """fastest/slowest에 style, elapsed_time 필드가 존재"""
        mock_cs.is_youtube_url.return_value = True
        mock_cs.get_video_id.return_value = 'test123'
        mock_cs.get_content_title.return_value = '테스트'
        mock_cs.truncate_text.side_effect = lambda t, m: t
        mock_fetch.return_value = ('자막', None, None, [], 'api', None)
        mock_create.return_value = {'title': '결과', 'content': '내용', 'html': '<p>내용</p>'}

        with self.app.app_context():
            self.app.config['STYLE_PROMPTS'] = {'summary': '요약', 'blog_seo': 'SEO'}

        resp = self.client.post('/api/generate-multi', json={
            'url': 'https://www.youtube.com/watch?v=test123',
            'styles': ['summary', 'blog_seo'],
        }, headers={'Origin': 'http://localhost:3000'})

        data = resp.get_json()
        for field in ('fastest_style', 'slowest_style'):
            self.assertIsNotNone(data[field])
            self.assertIn('style', data[field])
            self.assertIn('elapsed_time', data[field])
            self.assertIsInstance(data[field]['elapsed_time'], float)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.ai_service.create_content')
    @patch('routes.advanced_routes._fetch_youtube_content')
    @patch('routes.advanced_routes.content_service')
    def test_all_errors_returns_null(self, mock_cs, mock_fetch, mock_create, mock_supa):
        """모든 스타일이 에러면 fastest/slowest는 null"""
        mock_cs.is_youtube_url.return_value = True
        mock_cs.get_video_id.return_value = 'test123'
        mock_cs.get_content_title.return_value = '테스트'
        mock_cs.truncate_text.side_effect = lambda t, m: t
        mock_fetch.return_value = ('자막', None, None, [], 'api', None)
        mock_create.side_effect = Exception('실패')

        with self.app.app_context():
            self.app.config['STYLE_PROMPTS'] = {'summary': '요약'}

        resp = self.client.post('/api/generate-multi', json={
            'url': 'https://www.youtube.com/watch?v=test123',
            'styles': ['summary'],
        }, headers={'Origin': 'http://localhost:3000'})

        data = resp.get_json()
        self.assertIsNone(data['fastest_style'])
        self.assertIsNone(data['slowest_style'])


if __name__ == '__main__':
    unittest.main()
