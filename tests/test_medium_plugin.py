"""Medium 플러그인 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.mcp.plugins.medium import MediumPlugin


class TestMediumPlugin(unittest.TestCase):
    """Medium 플러그인 테스트"""

    def setUp(self):
        self.plugin = MediumPlugin()

    def test_name_and_description(self):
        """플러그인 메타데이터"""
        self.assertEqual(self.plugin.name, 'Medium')
        self.assertIn('Medium', self.plugin.description)

    def test_schema_has_api_token(self):
        """스키마에 api_token 필수 필드"""
        schema = self.plugin.schema()
        self.assertIn('api_token', schema['properties'])
        self.assertIn('api_token', schema['required'])

    def test_missing_token(self):
        """토큰 없이 실행 시 실패"""
        result = self.plugin.execute('내용', '제목')
        self.assertFalse(result['success'])
        self.assertIn('토큰', result['message'])

    @patch('services.mcp.plugins.medium.requests.get')
    @patch('services.mcp.plugins.medium.requests.post')
    def test_successful_post(self, mock_post, mock_get):
        """성공적인 포스트 생성"""
        # /me 응답
        me_resp = MagicMock()
        me_resp.status_code = 200
        me_resp.json.return_value = {'data': {'id': 'user-123'}}
        mock_get.return_value = me_resp

        # 포스트 생성 응답
        post_resp = MagicMock()
        post_resp.status_code = 201
        post_resp.json.return_value = {'data': {'url': 'https://medium.com/@user/post-123'}}
        mock_post.return_value = post_resp

        result = self.plugin.execute('내용', '제목', api_token='fake-token')
        self.assertTrue(result['success'])
        self.assertIn('medium.com', result['url'])

    @patch('services.mcp.plugins.medium.requests.get')
    def test_auth_failure(self, mock_get):
        """인증 실패"""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp

        result = self.plugin.execute('내용', '제목', api_token='bad-token')
        self.assertFalse(result['success'])
        self.assertIn('인증', result['message'])

    @patch('services.mcp.plugins.medium.requests.get')
    def test_connection_error(self, mock_get):
        """연결 오류"""
        import requests
        mock_get.side_effect = requests.RequestException('timeout')

        result = self.plugin.execute('내용', '제목', api_token='fake-token')
        self.assertFalse(result['success'])


if __name__ == '__main__':
    unittest.main()
