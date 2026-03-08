"""Google Sheets Service 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.integrations.gsheets_service import GoogleSheetsService


class TestGoogleSheetsService(unittest.TestCase):

    def test_is_configured_false(self):
        svc = GoogleSheetsService()
        svc.api_key = ''
        svc.spreadsheet_id = ''
        self.assertFalse(svc.is_configured)

    def test_is_configured_true(self):
        svc = GoogleSheetsService()
        svc.api_key = 'AIza...'
        svc.spreadsheet_id = 'sheet123'
        self.assertTrue(svc.is_configured)

    def test_append_row_not_configured(self):
        svc = GoogleSheetsService()
        svc.api_key = ''
        svc.spreadsheet_id = ''
        result = svc.append_row(['a', 'b'])
        self.assertFalse(result['success'])

    def test_sync_content_not_configured(self):
        svc = GoogleSheetsService()
        svc.api_key = ''
        svc.spreadsheet_id = ''
        result = svc.sync_content('제목', '본문', 'blog_seo')
        self.assertFalse(result['success'])
        self.assertIn('설정되지 않았습니다', result['message'])

    @patch.object(GoogleSheetsService, 'append_row')
    def test_sync_content_success(self, mock_append):
        mock_append.return_value = {
            'updates': {'updatedRange': 'Contents!A2:E2'}
        }
        svc = GoogleSheetsService()
        svc.api_key = 'key'
        svc.spreadsheet_id = 'sheet_id'
        result = svc.sync_content('제목', '본문', 'blog_seo')
        self.assertTrue(result['success'])
        self.assertIn('동기화 완료', result['message'])

    @patch.object(GoogleSheetsService, 'append_row')
    def test_sync_content_api_error(self, mock_append):
        mock_append.side_effect = ValueError('Sheets API 오류 (403): forbidden')
        svc = GoogleSheetsService()
        svc.api_key = 'key'
        svc.spreadsheet_id = 'sheet_id'
        result = svc.sync_content('제목', '본문', 'blog_seo')
        self.assertFalse(result['success'])
        self.assertIn('403', result['message'])

    @patch.object(GoogleSheetsService, 'append_row')
    def test_sync_content_generic_error(self, mock_append):
        mock_append.side_effect = Exception('timeout')
        svc = GoogleSheetsService()
        svc.api_key = 'key'
        svc.spreadsheet_id = 'sheet_id'
        result = svc.sync_content('제목', '본문', 'blog_seo')
        self.assertFalse(result['success'])

    @patch.object(GoogleSheetsService, 'append_row')
    def test_ensure_header_row_success(self, mock_append):
        mock_append.return_value = {}
        svc = GoogleSheetsService()
        svc.api_key = 'key'
        svc.spreadsheet_id = 'sheet_id'
        self.assertTrue(svc.ensure_header_row())

    @patch.object(GoogleSheetsService, 'append_row')
    def test_ensure_header_row_failure(self, mock_append):
        mock_append.side_effect = Exception('error')
        svc = GoogleSheetsService()
        svc.api_key = 'key'
        svc.spreadsheet_id = 'sheet_id'
        self.assertFalse(svc.ensure_header_row())

    def test_get_access_token_no_json(self):
        svc = GoogleSheetsService()
        svc._service_account_json = ''
        self.assertIsNone(svc._get_access_token())

    @patch.object(GoogleSheetsService, 'append_row')
    def test_sync_content_truncates_content(self, mock_append):
        mock_append.return_value = {'updates': {'updatedRange': 'A1'}}
        svc = GoogleSheetsService()
        svc.api_key = 'key'
        svc.spreadsheet_id = 'sheet_id'
        long_content = 'X' * 100000
        svc.sync_content('제목', long_content, 'blog_seo')
        row = mock_append.call_args[0][0]
        self.assertLessEqual(len(row[4]), 50000)


if __name__ == '__main__':
    unittest.main()
