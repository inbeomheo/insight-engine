"""Airtable Service 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.integrations.airtable_service import AirtableService


class TestAirtableService(unittest.TestCase):

    def test_is_configured_false(self):
        with patch.dict('os.environ', {'AIRTABLE_API_KEY': '', 'AIRTABLE_BASE_ID': ''}, clear=False):
            svc = AirtableService()
            svc.api_key = ''
            svc.base_id = ''
            self.assertFalse(svc.is_configured)

    def test_is_configured_true(self):
        svc = AirtableService()
        svc.api_key = 'key123'
        svc.base_id = 'app123'
        self.assertTrue(svc.is_configured)

    def test_headers_contain_auth(self):
        svc = AirtableService()
        svc.api_key = 'patXYZ'
        headers = svc._headers()
        self.assertEqual(headers['Authorization'], 'Bearer patXYZ')
        self.assertEqual(headers['Content-Type'], 'application/json')

    def test_sync_content_not_configured(self):
        svc = AirtableService()
        svc.api_key = ''
        svc.base_id = ''
        result = svc.sync_content('제목', '본문', 'blog_seo')
        self.assertFalse(result['success'])
        self.assertIn('설정되지 않았습니다', result['message'])

    @patch.object(AirtableService, 'create_record')
    def test_sync_content_success(self, mock_create):
        mock_create.return_value = {'id': 'rec123'}
        svc = AirtableService()
        svc.api_key = 'key'
        svc.base_id = 'base'
        result = svc.sync_content('제목', '본문', 'blog_seo', url='https://youtube.com/watch?v=test')
        self.assertTrue(result['success'])
        self.assertEqual(result['record_id'], 'rec123')

    @patch.object(AirtableService, 'create_record')
    def test_sync_content_api_error(self, mock_create):
        mock_create.side_effect = ValueError('Airtable API 오류 (422): bad field')
        svc = AirtableService()
        svc.api_key = 'key'
        svc.base_id = 'base'
        result = svc.sync_content('제목', '본문', 'blog_seo')
        self.assertFalse(result['success'])
        self.assertIn('422', result['message'])

    @patch.object(AirtableService, 'create_record')
    def test_sync_content_generic_error(self, mock_create):
        mock_create.side_effect = Exception('network error')
        svc = AirtableService()
        svc.api_key = 'key'
        svc.base_id = 'base'
        result = svc.sync_content('제목', '본문', 'blog_seo')
        self.assertFalse(result['success'])

    @patch('services.integrations.airtable_service.urllib.request.urlopen')
    def test_list_records_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"records": [{"id": "rec1"}, {"id": "rec2"}]}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        svc = AirtableService()
        svc.api_key = 'key'
        svc.base_id = 'base'
        records = svc.list_records('Contents')
        self.assertEqual(len(records), 2)

    @patch('services.integrations.airtable_service.urllib.request.urlopen')
    def test_list_records_error(self, mock_urlopen):
        mock_urlopen.side_effect = Exception('timeout')
        svc = AirtableService()
        svc.api_key = 'key'
        svc.base_id = 'base'
        records = svc.list_records('Contents')
        self.assertEqual(records, [])

    def test_sync_content_truncates_title(self):
        svc = AirtableService()
        svc.api_key = 'key'
        svc.base_id = 'base'
        long_title = 'A' * 500
        with patch.object(svc, 'create_record', return_value={'id': 'rec_x'}) as mock_create:
            svc.sync_content(long_title, '본문', 'blog_seo')
            fields = mock_create.call_args[0][1]
            self.assertLessEqual(len(fields['Title']), 255)


if __name__ == '__main__':
    unittest.main()
