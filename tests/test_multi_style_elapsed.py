"""R28: 멀티스타일 생성 응답에 스타일별 처리 시간(style_elapsed_time) 포함 테스트"""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch, MagicMock

from app import create_app


class TestMultiStyleElapsedTime(unittest.TestCase):
    """generate-multi 응답의 style_elapsed_time 필드 검증"""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.ai_service.create_content')
    @patch('routes.advanced_routes._fetch_youtube_content')
    @patch('routes.advanced_routes.content_service')
    def test_each_result_has_style_elapsed_time(
        self, mock_cs, mock_fetch, mock_create, mock_supa
    ):
        """각 스타일 결과에 style_elapsed_time 필드가 존재하는지 확인"""
        mock_cs.is_youtube_url.return_value = True
        mock_cs.get_video_id.return_value = 'test123'
        mock_cs.get_content_title.return_value = '테스트'
        mock_cs.truncate_text.side_effect = lambda t, m: t
        mock_fetch.return_value = ('자막 텍스트', None, None, [], 'api', None)
        mock_create.return_value = {'title': '결과', 'content': '내용', 'html': '<p>내용</p>'}

        with self.app.app_context():
            self.app.config['STYLE_PROMPTS'] = {'summary': '요약', 'blog_seo': 'SEO'}

        resp = self.client.post('/api/generate-multi', json={
            'url': 'https://www.youtube.com/watch?v=test123',
            'styles': ['summary', 'blog_seo'],
        }, headers={'Origin': 'http://localhost:3000'})

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get('success'))
        for result in data['results']:
            self.assertIn('style_elapsed_time', result)
            self.assertIsInstance(result['style_elapsed_time'], float)
            self.assertGreaterEqual(result['style_elapsed_time'], 0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.ai_service.create_content')
    @patch('routes.advanced_routes._fetch_youtube_content')
    @patch('routes.advanced_routes.content_service')
    def test_error_result_also_has_style_elapsed_time(
        self, mock_cs, mock_fetch, mock_create, mock_supa
    ):
        """에러 발생 시에도 style_elapsed_time 필드가 포함되는지 확인"""
        mock_cs.is_youtube_url.return_value = True
        mock_cs.get_video_id.return_value = 'test123'
        mock_cs.get_content_title.return_value = '테스트'
        mock_cs.truncate_text.side_effect = lambda t, m: t
        mock_fetch.return_value = ('자막 텍스트', None, None, [], 'api', None)
        mock_create.side_effect = Exception('AI 호출 실패')

        with self.app.app_context():
            self.app.config['STYLE_PROMPTS'] = {'summary': '요약'}

        resp = self.client.post('/api/generate-multi', json={
            'url': 'https://www.youtube.com/watch?v=test123',
            'styles': ['summary'],
        }, headers={'Origin': 'http://localhost:3000'})

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        for result in data['results']:
            self.assertIn('style_elapsed_time', result)
            self.assertIn('error', result)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.ai_service.create_content')
    @patch('routes.advanced_routes._fetch_youtube_content')
    @patch('routes.advanced_routes.content_service')
    def test_total_elapsed_time_still_present(
        self, mock_cs, mock_fetch, mock_create, mock_supa
    ):
        """기존 전체 elapsed_time 필드가 여전히 존재하는지 확인"""
        mock_cs.is_youtube_url.return_value = True
        mock_cs.get_video_id.return_value = 'test123'
        mock_cs.get_content_title.return_value = '테스트'
        mock_cs.truncate_text.side_effect = lambda t, m: t
        mock_fetch.return_value = ('자막 텍스트', None, None, [], 'api', None)
        mock_create.return_value = {'title': '결과', 'content': '내용', 'html': '<p>내용</p>'}

        with self.app.app_context():
            self.app.config['STYLE_PROMPTS'] = {'summary': '요약'}

        resp = self.client.post('/api/generate-multi', json={
            'url': 'https://www.youtube.com/watch?v=test123',
            'styles': ['summary'],
        }, headers={'Origin': 'http://localhost:3000'})

        data = resp.get_json()
        self.assertIn('elapsed_time', data)
        self.assertIsInstance(data['elapsed_time'], float)


if __name__ == '__main__':
    unittest.main()
