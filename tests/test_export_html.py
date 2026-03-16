"""HTML 내보내기 API 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestExportHtml(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_exports_html_file(self, _mock_sb):
        """HTML 파일로 다운로드."""
        resp = self.client.post('/api/export/html',
                                json={'title': '테스트 제목', 'html': '<p>본문</p>'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/html', resp.content_type)
        html = resp.data.decode('utf-8')
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('테스트 제목', html)
        self.assertIn('<p>본문</p>', html)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_empty_content_returns_400(self, _mock_sb):
        """빈 콘텐츠는 400."""
        resp = self.client.post('/api/export/html',
                                json={'title': 'x', 'html': ''},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_includes_inline_css(self, _mock_sb):
        """인라인 CSS 포함."""
        resp = self.client.post('/api/export/html',
                                json={'title': 'CSS 테스트', 'html': '<p>ok</p>'},
                                headers=_HEADERS)
        html = resp.data.decode('utf-8')
        self.assertIn('<style>', html)
        self.assertIn('font-family', html)


if __name__ == '__main__':
    unittest.main()
