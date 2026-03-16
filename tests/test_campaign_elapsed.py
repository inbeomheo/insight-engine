"""캠페인 생성 응답의 total_elapsed_time / 개별 elapsed_time 테스트."""
import unittest
from unittest.mock import patch, MagicMock

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestCampaignElapsedTime(unittest.TestCase):
    """generate-campaign 응답에 시간 메타 포함 검증."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.advanced_routes._fetch_youtube_content')
    @patch('routes.advanced_routes.ai_service')
    @patch('routes.advanced_routes.content_service')
    def test_total_elapsed_time_in_response(self, mock_cs, mock_ai, mock_fetch, _mock_sb):
        """응답에 total_elapsed_time 필드 포함."""
        mock_cs.is_youtube_url.return_value = True
        mock_cs.get_video_id.return_value = 'abc123'
        mock_cs.get_content_title.return_value = '테스트 영상'
        mock_cs.truncate_text.return_value = '자막 텍스트'
        mock_fetch.return_value = ('자막', [], None, [], 'youtube-transcript-api', None)
        mock_ai.create_content.return_value = {
            'content': '결과',
            'title': '제목',
            'html': '<p>결과</p>',
            'usage': {'total_tokens': 100, 'input_tokens': 50, 'output_tokens': 50},
        }

        resp = self.client.post('/api/generate-campaign',
                                json={
                                    'url': 'https://www.youtube.com/watch?v=abc123',
                                    'pack_id': 'full',
                                },
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('total_elapsed_time', data)
        self.assertIn('elapsed_time', data)
        self.assertIsInstance(data['total_elapsed_time'], float)
        self.assertEqual(data['elapsed_time'], data['total_elapsed_time'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.advanced_routes._fetch_youtube_content')
    @patch('routes.advanced_routes.ai_service')
    @patch('routes.advanced_routes.content_service')
    def test_per_style_elapsed_time(self, mock_cs, mock_ai, mock_fetch, _mock_sb):
        """각 스타일 결과에 elapsed_time 포함."""
        mock_cs.is_youtube_url.return_value = True
        mock_cs.get_video_id.return_value = 'abc123'
        mock_cs.get_content_title.return_value = '테스트'
        mock_cs.truncate_text.return_value = '자막'
        mock_fetch.return_value = ('자막', [], None, [], 'api', None)
        mock_ai.create_content.return_value = {
            'content': '결과',
            'title': '제목',
            'html': '<p></p>',
            'usage': {'total_tokens': 10, 'input_tokens': 5, 'output_tokens': 5},
        }

        resp = self.client.post('/api/generate-campaign',
                                json={
                                    'url': 'https://www.youtube.com/watch?v=abc123',
                                    'pack_id': 'full',
                                },
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        for result in data['results']:
            self.assertIn('elapsed_time', result)
            self.assertIsInstance(result['elapsed_time'], float)


if __name__ == '__main__':
    unittest.main()
