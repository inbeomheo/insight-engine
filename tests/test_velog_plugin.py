"""VelogPlugin 단위 테스트"""
import json
import unittest
from unittest.mock import patch, MagicMock

from services.mcp.plugins.velog import VelogPlugin


class TestVelogPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = VelogPlugin()

    def test_name_and_description(self):
        self.assertEqual(self.plugin.name, "Velog")
        self.assertIn("Velog", self.plugin.description)

    def test_schema_requires_access_token(self):
        schema = self.plugin.schema()
        self.assertIn("access_token", schema["required"])
        self.assertEqual(schema["type"], "object")

    def test_execute_no_token_returns_error(self):
        with patch.dict('os.environ', {}, clear=True):
            result = self.plugin.execute("본문", "제목")
        self.assertFalse(result["success"])
        self.assertIn("토큰", result["message"])

    @patch('services.mcp.plugins.velog.urllib.request.urlopen')
    def test_execute_success(self, mock_urlopen):
        response_data = {
            'data': {
                'writePost': {
                    'id': 'post-123',
                    'url_slug': 'test-title',
                    'user': {'username': 'testuser'},
                }
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = self.plugin.execute("본문", "제목", access_token="tok-123", tags=["python"])
        self.assertTrue(result["success"])
        self.assertIn("post-123", result["message"])
        self.assertEqual(result["url"], "https://velog.io/@testuser/test-title")

    @patch('services.mcp.plugins.velog.urllib.request.urlopen')
    def test_execute_graphql_error(self, mock_urlopen):
        response_data = {'errors': [{'message': '인증 실패'}]}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = self.plugin.execute("본문", "제목", access_token="bad-token")
        self.assertFalse(result["success"])
        self.assertIn("인증 실패", result["message"])

    @patch('services.mcp.plugins.velog.urllib.request.urlopen')
    def test_execute_http_error(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='', code=500, msg='Server Error', hdrs=None, fp=None
        )
        result = self.plugin.execute("본문", "제목", access_token="tok")
        self.assertFalse(result["success"])
        self.assertIn("500", result["message"])

    @patch('services.mcp.plugins.velog.urllib.request.urlopen')
    def test_execute_with_series_id(self, mock_urlopen):
        response_data = {
            'data': {'writePost': {'id': 'p1', 'url_slug': 'slug', 'user': {'username': 'u'}}}
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = self.plugin.execute("본문", "제목", access_token="tok", series_id="s-1")
        self.assertTrue(result["success"])


if __name__ == '__main__':
    unittest.main()
