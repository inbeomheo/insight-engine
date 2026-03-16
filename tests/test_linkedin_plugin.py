"""LinkedInPlugin 단위 테스트"""
import json
import unittest
from unittest.mock import patch, MagicMock

from services.mcp.plugins.linkedin import LinkedInPlugin


class TestLinkedInPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = LinkedInPlugin()

    def test_name_and_description(self):
        self.assertEqual(self.plugin.name, "LinkedIn")
        self.assertIn("LinkedIn", self.plugin.description)

    def test_schema_requires_access_token(self):
        schema = self.plugin.schema()
        self.assertIn("access_token", schema["required"])
        self.assertIn("visibility", schema["properties"])

    def test_execute_no_token(self):
        with patch.dict('os.environ', {}, clear=True):
            result = self.plugin.execute("본문", "제목")
        self.assertFalse(result["success"])
        self.assertIn("토큰", result["message"])

    @patch('services.mcp.plugins.linkedin.urllib.request.urlopen')
    def test_execute_success_with_author_urn(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.headers = {'x-restli-id': 'urn:li:ugcPost:12345'}
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = self.plugin.execute(
            "본문", "제목",
            access_token="tok-abc",
            author_urn="urn:li:person:ABC",
        )
        self.assertTrue(result["success"])
        self.assertIn("12345", result["url"])

    @patch('services.mcp.plugins.linkedin.urllib.request.urlopen')
    def test_execute_fetches_author_urn_if_missing(self, mock_urlopen):
        # 첫 호출: /me → 사용자 ID 반환
        me_resp = MagicMock()
        me_resp.read.return_value = json.dumps({"id": "USER1"}).encode()
        me_resp.__enter__ = MagicMock(return_value=me_resp)
        me_resp.__exit__ = MagicMock(return_value=False)
        # 두 번째 호출: /ugcPosts → 포스트 게시
        post_resp = MagicMock()
        post_resp.headers = {'x-restli-id': 'urn:li:ugcPost:999'}
        post_resp.__enter__ = MagicMock(return_value=post_resp)
        post_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.side_effect = [me_resp, post_resp]

        with patch.dict('os.environ', {}, clear=True):
            result = self.plugin.execute("본문", "제목", access_token="tok")
        self.assertTrue(result["success"])

    @patch('services.mcp.plugins.linkedin.urllib.request.urlopen')
    def test_execute_me_fetch_failure(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("네트워크 오류")
        with patch.dict('os.environ', {}, clear=True):
            result = self.plugin.execute("본문", "제목", access_token="tok")
        self.assertFalse(result["success"])
        self.assertIn("사용자 정보", result["message"])

    @patch('services.mcp.plugins.linkedin.urllib.request.urlopen')
    def test_execute_http_error(self, mock_urlopen):
        import urllib.error
        # 첫 호출 성공 (author_urn 제공하므로 /me 안 탐), 두 번째에서 HTTPError
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='', code=403, msg='Forbidden', hdrs=None, fp=MagicMock(read=lambda: b'{"msg":"forbidden"}')
        )
        result = self.plugin.execute("본문", "제목", access_token="tok", author_urn="urn:li:person:X")
        self.assertFalse(result["success"])
        self.assertIn("403", result["message"])

    def test_execute_truncates_to_3000_chars(self):
        """3000자 초과 콘텐츠가 잘리는지 확인"""
        long_content = "A" * 5000
        with patch('services.mcp.plugins.linkedin.urllib.request.urlopen') as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.headers = {'x-restli-id': 'id-1'}
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = self.plugin.execute(long_content, "T", access_token="tok", author_urn="urn:li:person:X")
            self.assertTrue(result["success"])
            # Request에 전달된 payload 확인
            call_args = mock_urlopen.call_args
            req = call_args[0][0]
            body = json.loads(req.data.decode())
            text = body['specificContent']['com.linkedin.ugc.ShareContent']['shareCommentary']['text']
            self.assertLessEqual(len(text), 3000)


if __name__ == '__main__':
    unittest.main()
