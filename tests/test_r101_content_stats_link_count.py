"""R101: /api/content/stats 응답에 link_count 필드 포함 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestContentStatsLinkCount(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_link_count_in_response(self, _mock_sb):
        """link_count 필드가 응답에 포함된다."""
        resp = self.client.post('/api/content/stats',
                                json={'content': '텍스트입니다.'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('link_count', data)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_link_count_zero_no_urls(self, _mock_sb):
        """URL이 없으면 link_count는 0."""
        resp = self.client.post('/api/content/stats',
                                json={'content': '링크 없는 일반 텍스트입니다.'},
                                headers=_HEADERS)
        data = resp.get_json()
        self.assertEqual(data['link_count'], 0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_link_count_multiple_urls(self, _mock_sb):
        """여러 URL이 있으면 정확히 카운트한다."""
        content = (
            '참고: https://example.com 그리고 '
            'http://test.org/page 마지막으로 '
            'https://docs.python.org/3/library.html 입니다.'
        )
        resp = self.client.post('/api/content/stats',
                                json={'content': content},
                                headers=_HEADERS)
        data = resp.get_json()
        self.assertEqual(data['link_count'], 3)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_link_count_markdown_links(self, _mock_sb):
        """마크다운 형식 링크도 카운트한다."""
        content = '[구글](https://google.com)과 [네이버](https://naver.com) 참고.'
        resp = self.client.post('/api/content/stats',
                                json={'content': content},
                                headers=_HEADERS)
        data = resp.get_json()
        self.assertEqual(data['link_count'], 2)


if __name__ == '__main__':
    unittest.main()
