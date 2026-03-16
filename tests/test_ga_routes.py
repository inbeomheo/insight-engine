"""Google Analytics 4 라우트 단위 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestGARoutes(unittest.TestCase):
    """GA4 페이지뷰 / 이벤트 API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.analytics.ga_service.GAService.get_page_views')
    def test_pageviews_success(self, mock_pv, _mock_sb):
        """페이지뷰 조회 성공."""
        mock_pv.return_value = {'enabled': True, 'days': 7, 'rows': []}
        resp = self.client.get('/api/admin/ga/pageviews?days=7', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['enabled'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.analytics.ga_service.GAService.get_page_views')
    def test_pageviews_disabled(self, mock_pv, _mock_sb):
        """GA4 미설정 시 enabled=False."""
        mock_pv.return_value = {'enabled': False, 'reason': 'GA4_PROPERTY_ID 미설정'}
        resp = self.client.get('/api/admin/ga/pageviews', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()['enabled'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.analytics.ga_service.GAService.get_event_counts')
    def test_events_success(self, mock_ev, _mock_sb):
        """이벤트 카운트 조회."""
        mock_ev.return_value = {'enabled': True, 'days': 30, 'rows': [{'event': 'click', 'count': 5}]}
        resp = self.client.get('/api/admin/ga/events', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()['rows']), 1)


if __name__ == '__main__':
    unittest.main()
