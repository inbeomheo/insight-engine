"""Google Analytics 4 Service 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.analytics.ga_service import GAService


class TestGAService(unittest.TestCase):

    def test_init_default_property(self):
        with patch('services.analytics.ga_service.GA4_PROPERTY_ID', '12345'):
            svc = GAService()
            self.assertEqual(svc.property_id, '12345')

    def test_init_custom_property(self):
        svc = GAService(property_id='99999')
        self.assertEqual(svc.property_id, '99999')

    @patch('services.analytics.ga_service.GOOGLE_APPLICATION_CREDENTIALS', '')
    def test_is_enabled_false_no_creds(self):
        svc = GAService(property_id='12345')
        self.assertFalse(svc.is_enabled())

    @patch('services.analytics.ga_service.GOOGLE_APPLICATION_CREDENTIALS', '/path/to/creds.json')
    def test_is_enabled_false_no_property(self):
        svc = GAService(property_id='')
        self.assertFalse(svc.is_enabled())

    @patch('services.analytics.ga_service.GOOGLE_APPLICATION_CREDENTIALS', '/path/to/creds.json')
    def test_is_enabled_true(self):
        svc = GAService(property_id='12345')
        self.assertTrue(svc.is_enabled())

    def test_get_page_views_disabled(self):
        svc = GAService(property_id='')
        result = svc.get_page_views()
        self.assertFalse(result['enabled'])

    @patch('services.analytics.ga_service.GOOGLE_APPLICATION_CREDENTIALS', '/path/creds.json')
    def test_get_page_views_no_package(self):
        svc = GAService(property_id='12345')
        svc._client = None
        with patch.object(svc, '_get_client', return_value=None):
            result = svc.get_page_views()
            self.assertFalse(result['enabled'])

    @patch('services.analytics.ga_service.GOOGLE_APPLICATION_CREDENTIALS', '/path/creds.json')
    def test_get_page_views_success(self):
        svc = GAService(property_id='12345')
        mock_client = MagicMock()
        mock_row = MagicMock()
        mock_row.dimension_values = [MagicMock(value='/blog/post1')]
        mock_row.metric_values = [MagicMock(value='150')]
        mock_response = MagicMock()
        mock_response.rows = [mock_row]
        mock_client.run_report.return_value = mock_response
        svc._client = mock_client

        mock_types = MagicMock()
        with patch.dict('sys.modules', {
            'google.analytics': MagicMock(),
            'google.analytics.data_v1beta': MagicMock(),
            'google.analytics.data_v1beta.types': mock_types,
        }):
            result = svc.get_page_views(days=7)
        self.assertTrue(result['enabled'])
        self.assertEqual(result['days'], 7)
        self.assertEqual(len(result['rows']), 1)
        self.assertEqual(result['rows'][0]['page'], '/blog/post1')
        self.assertEqual(result['rows'][0]['views'], 150)

    @patch('services.analytics.ga_service.GOOGLE_APPLICATION_CREDENTIALS', '/path/creds.json')
    def test_get_page_views_api_error(self):
        svc = GAService(property_id='12345')
        mock_client = MagicMock()
        mock_client.run_report.side_effect = Exception('API error')
        svc._client = mock_client

        mock_types = MagicMock()
        with patch.dict('sys.modules', {
            'google.analytics': MagicMock(),
            'google.analytics.data_v1beta': MagicMock(),
            'google.analytics.data_v1beta.types': mock_types,
        }):
            result = svc.get_page_views()
        self.assertTrue(result['enabled'])
        self.assertIn('error', result)

    def test_get_event_counts_disabled(self):
        svc = GAService(property_id='')
        result = svc.get_event_counts()
        self.assertFalse(result['enabled'])

    @patch('services.analytics.ga_service.GOOGLE_APPLICATION_CREDENTIALS', '/path/creds.json')
    def test_get_event_counts_success(self):
        svc = GAService(property_id='12345')
        mock_client = MagicMock()
        mock_row = MagicMock()
        mock_row.dimension_values = [MagicMock(value='page_view')]
        mock_row.metric_values = [MagicMock(value='500')]
        mock_response = MagicMock()
        mock_response.rows = [mock_row]
        mock_client.run_report.return_value = mock_response
        svc._client = mock_client

        mock_types = MagicMock()
        with patch.dict('sys.modules', {
            'google.analytics': MagicMock(),
            'google.analytics.data_v1beta': MagicMock(),
            'google.analytics.data_v1beta.types': mock_types,
        }):
            result = svc.get_event_counts(days=14)
        self.assertTrue(result['enabled'])
        self.assertEqual(result['rows'][0]['event'], 'page_view')
        self.assertEqual(result['rows'][0]['count'], 500)


if __name__ == '__main__':
    unittest.main()
