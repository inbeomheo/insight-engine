"""Substack 플러그인 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.mcp.plugins.substack import SubstackPlugin


class TestSubstackPlugin(unittest.TestCase):
    """Substack 플러그인 테스트"""

    def setUp(self):
        self.plugin = SubstackPlugin()

    def test_name_and_description(self):
        """플러그인 메타데이터"""
        self.assertEqual(self.plugin.name, 'Substack')
        self.assertIn('Substack', self.plugin.description)

    def test_schema_required_fields(self):
        """스키마에 필수 필드"""
        schema = self.plugin.schema()
        self.assertIn('subdomain', schema['required'])
        self.assertIn('api_key', schema['required'])

    def test_missing_credentials(self):
        """인증 정보 없이 실행 시 실패"""
        result = self.plugin.execute('내용', '제목')
        self.assertFalse(result['success'])
        self.assertIn('서브도메인', result['message'])

    @patch('services.mcp.plugins.substack.requests.post')
    def test_successful_draft(self, mock_post):
        """성공적인 Draft 생성"""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {'id': 'post-456'}
        mock_post.return_value = mock_resp

        result = self.plugin.execute(
            '내용', '제목',
            subdomain='mysite', api_key='fake-key'
        )
        self.assertTrue(result['success'])
        self.assertIn('mysite.substack.com', result['url'])

    @patch('services.mcp.plugins.substack.requests.post')
    def test_api_error(self, mock_post):
        """API 오류"""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        result = self.plugin.execute(
            '내용', '제목',
            subdomain='mysite', api_key='fake-key'
        )
        self.assertFalse(result['success'])

    @patch('services.mcp.plugins.substack.requests.post')
    def test_connection_error(self, mock_post):
        """연결 오류"""
        import requests
        mock_post.side_effect = requests.RequestException('timeout')

        result = self.plugin.execute(
            '내용', '제목',
            subdomain='mysite', api_key='fake-key'
        )
        self.assertFalse(result['success'])


if __name__ == '__main__':
    unittest.main()
