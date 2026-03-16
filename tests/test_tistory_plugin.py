"""TistoryPlugin 단위 테스트"""
import json
import unittest
from unittest.mock import patch, MagicMock

from services.mcp.plugins.tistory import TistoryPlugin


class TestTistoryPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = TistoryPlugin()

    def test_name_and_description(self):
        self.assertEqual(self.plugin.name, "Tistory")
        self.assertIn("Tistory", self.plugin.description)

    def test_schema_requires_token_and_blog_name(self):
        schema = self.plugin.schema()
        self.assertIn("access_token", schema["required"])
        self.assertIn("blog_name", schema["required"])

    def test_execute_no_token(self):
        with patch.dict('os.environ', {}, clear=True):
            result = self.plugin.execute("본문", "제목", blog_name="myblog")
        self.assertFalse(result["success"])
        self.assertIn("토큰", result["message"])

    def test_execute_no_blog_name(self):
        with patch.dict('os.environ', {}, clear=True):
            result = self.plugin.execute("본문", "제목", access_token="tok")
        self.assertFalse(result["success"])
        self.assertIn("블로그 이름", result["message"])

    @patch('services.mcp.plugins.tistory.urllib.request.urlopen')
    def test_execute_success(self, mock_urlopen):
        response_data = {
            'tistory': {
                'status': '200',
                'postId': '42',
                'url': 'https://myblog.tistory.com/42',
            }
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = self.plugin.execute(
            "본문 내용", "테스트 제목",
            access_token="tok", blog_name="myblog",
        )
        self.assertTrue(result["success"])
        self.assertIn("42", result["message"])
        self.assertEqual(result["url"], "https://myblog.tistory.com/42")

    @patch('services.mcp.plugins.tistory.urllib.request.urlopen')
    def test_execute_api_error(self, mock_urlopen):
        response_data = {
            'tistory': {'status': '400', 'error_message': '잘못된 요청'}
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = self.plugin.execute("본문", "제목", access_token="tok", blog_name="myblog")
        self.assertFalse(result["success"])
        self.assertIn("잘못된 요청", result["message"])

    @patch('services.mcp.plugins.tistory.urllib.request.urlopen')
    def test_execute_http_error(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='', code=401, msg='Unauthorized', hdrs=None, fp=None
        )
        result = self.plugin.execute("본문", "제목", access_token="tok", blog_name="myblog")
        self.assertFalse(result["success"])
        self.assertIn("401", result["message"])

    @patch('services.mcp.plugins.tistory.urllib.request.urlopen')
    def test_execute_generic_exception(self, mock_urlopen):
        mock_urlopen.side_effect = ConnectionError("타임아웃")
        result = self.plugin.execute("본문", "제목", access_token="tok", blog_name="myblog")
        self.assertFalse(result["success"])
        self.assertIn("타임아웃", result["message"])


if __name__ == '__main__':
    unittest.main()
