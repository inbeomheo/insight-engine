"""Google Search Console 라우트 단위 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestGSCRoutes(unittest.TestCase):
    """GSC 검색 분석 / 페이지 성과 API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.analytics.gsc_service.GSCService.get_search_analytics')
    def test_search_analytics(self, mock_sa, _mock_sb):
        """검색어 분석 조회."""
        mock_sa.return_value = {'enabled': True, 'rows': [{'query': 'test', 'clicks': 10}]}
        resp = self.client.get('/api/admin/gsc/search-analytics?days=14', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['enabled'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.analytics.gsc_service.GSCService.get_search_analytics')
    def test_search_analytics_disabled(self, mock_sa, _mock_sb):
        """GSC 미설정 시 enabled=False."""
        mock_sa.return_value = {'enabled': False, 'reason': 'GSC_SITE_URL 미설정'}
        resp = self.client.get('/api/admin/gsc/search-analytics', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()['enabled'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.analytics.gsc_service.GSCService.get_top_pages')
    def test_top_pages(self, mock_tp, _mock_sb):
        """페이지별 성과 조회."""
        mock_tp.return_value = {'enabled': True, 'rows': []}
        resp = self.client.get('/api/admin/gsc/top-pages', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)


if __name__ == '__main__':
    unittest.main()
