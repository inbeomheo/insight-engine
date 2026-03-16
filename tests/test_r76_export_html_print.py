"""R76: /api/export/html print_friendly 옵션 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestExportHtmlPrintFriendly(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_print_friendly_adds_media_print(self, _mock):
        """print_friendly=true 시 @media print CSS 포함."""
        resp = self.client.post('/api/export/html',
                                json={'title': '인쇄', 'html': '<p>본문</p>',
                                      'print_friendly': True},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode('utf-8')
        self.assertIn('@media print', html)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_print_friendly_shows_link_urls(self, _mock):
        """@media print CSS에 링크 URL 표시 규칙 포함."""
        resp = self.client.post('/api/export/html',
                                json={'title': '인쇄', 'html': '<p>ok</p>',
                                      'print_friendly': True},
                                headers=_HEADERS)
        html = resp.data.decode('utf-8')
        self.assertIn('attr(href)', html)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_print_friendly_pre_wrap(self, _mock):
        """@media print CSS에 pre-wrap 포함."""
        resp = self.client.post('/api/export/html',
                                json={'title': '인쇄', 'html': '<pre>code</pre>',
                                      'print_friendly': True},
                                headers=_HEADERS)
        html = resp.data.decode('utf-8')
        self.assertIn('pre-wrap', html)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_no_print_friendly_by_default(self, _mock):
        """기본값은 @media print 미포함."""
        resp = self.client.post('/api/export/html',
                                json={'title': '기본', 'html': '<p>ok</p>'},
                                headers=_HEADERS)
        html = resp.data.decode('utf-8')
        self.assertNotIn('@media print', html)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_print_friendly_with_dark_mode(self, _mock):
        """print_friendly + dark_mode 동시 사용 가능."""
        resp = self.client.post('/api/export/html',
                                json={'title': '혼합', 'html': '<p>ok</p>',
                                      'print_friendly': True, 'dark_mode': True},
                                headers=_HEADERS)
        html = resp.data.decode('utf-8')
        self.assertIn('@media print', html)
        self.assertIn('prefers-color-scheme: dark', html)


if __name__ == '__main__':
    unittest.main()
