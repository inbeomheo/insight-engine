"""Google Search Console Service 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.analytics.gsc_service import GSCService


class TestGSCService(unittest.TestCase):

    def test_init_default_site_url(self):
        with patch('services.analytics.gsc_service.GSC_SITE_URL', 'https://example.com'):
            svc = GSCService()
            self.assertEqual(svc.site_url, 'https://example.com')

    def test_init_custom_site_url(self):
        svc = GSCService(site_url='https://custom.com')
        self.assertEqual(svc.site_url, 'https://custom.com')

    @patch('services.analytics.gsc_service.GOOGLE_APPLICATION_CREDENTIALS', '')
    def test_is_enabled_false_no_creds(self):
        svc = GSCService(site_url='https://example.com')
        self.assertFalse(svc.is_enabled())

    @patch('services.analytics.gsc_service.GOOGLE_APPLICATION_CREDENTIALS', '/path/creds.json')
    def test_is_enabled_false_no_site(self):
        svc = GSCService(site_url='')
        self.assertFalse(svc.is_enabled())

    @patch('services.analytics.gsc_service.GOOGLE_APPLICATION_CREDENTIALS', '/path/creds.json')
    def test_is_enabled_true(self):
        svc = GSCService(site_url='https://example.com')
        self.assertTrue(svc.is_enabled())

    def test_get_search_analytics_disabled(self):
        svc = GSCService(site_url='')
        result = svc.get_search_analytics()
        self.assertFalse(result['enabled'])
        self.assertIn('reason', result)

    @patch('services.analytics.gsc_service.GOOGLE_APPLICATION_CREDENTIALS', '/path/creds.json')
    def test_get_search_analytics_no_service(self):
        svc = GSCService(site_url='https://example.com')
        with patch.object(svc, '_get_service', return_value=None):
            result = svc.get_search_analytics()
            self.assertFalse(result['enabled'])

    @patch('services.analytics.gsc_service.GOOGLE_APPLICATION_CREDENTIALS', '/path/creds.json')
    def test_get_search_analytics_success(self):
        svc = GSCService(site_url='https://example.com')
        mock_service = MagicMock()
        mock_execute = MagicMock(return_value={
            'rows': [
                {'keys': ['python tutorial'], 'clicks': 100, 'impressions': 5000,
                 'ctr': 0.02, 'position': 3.5},
            ]
        })
        mock_service.searchanalytics().query().execute = mock_execute
        svc._service = mock_service

        result = svc.get_search_analytics(days=7, row_limit=10)
        self.assertTrue(result['enabled'])
        self.assertEqual(len(result['rows']), 1)
        self.assertEqual(result['rows'][0]['query'], 'python tutorial')
        self.assertEqual(result['rows'][0]['clicks'], 100)
        self.assertEqual(result['rows'][0]['ctr'], 2.0)

    @patch('services.analytics.gsc_service.GOOGLE_APPLICATION_CREDENTIALS', '/path/creds.json')
    def test_get_search_analytics_api_error(self):
        svc = GSCService(site_url='https://example.com')
        mock_service = MagicMock()
        mock_service.searchanalytics().query().execute.side_effect = Exception('API fail')
        svc._service = mock_service

        result = svc.get_search_analytics()
        self.assertTrue(result['enabled'])
        self.assertIn('error', result)

    def test_get_top_pages_disabled(self):
        svc = GSCService(site_url='')
        result = svc.get_top_pages()
        self.assertFalse(result['enabled'])

    @patch('services.analytics.gsc_service.GOOGLE_APPLICATION_CREDENTIALS', '/path/creds.json')
    def test_get_top_pages_success(self):
        svc = GSCService(site_url='https://example.com')
        mock_service = MagicMock()
        mock_execute = MagicMock(return_value={
            'rows': [
                {'keys': ['/blog/post'], 'clicks': 50, 'impressions': 2000,
                 'ctr': 0.025, 'position': 5.2},
            ]
        })
        mock_service.searchanalytics().query().execute = mock_execute
        svc._service = mock_service

        result = svc.get_top_pages(days=14)
        self.assertTrue(result['enabled'])
        self.assertEqual(result['rows'][0]['page'], '/blog/post')


if __name__ == '__main__':
    unittest.main()
