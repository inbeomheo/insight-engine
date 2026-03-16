"""TwitterPlugin 단위 테스트"""
import json
import unittest
from unittest.mock import patch, MagicMock

from services.mcp.plugins.twitter import TwitterPlugin


class TestTwitterPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = TwitterPlugin()

    def test_name_and_description(self):
        self.assertEqual(self.plugin.name, "Twitter/X")
        self.assertIn("Twitter", self.plugin.description)

    def test_schema_requires_bearer_token(self):
        schema = self.plugin.schema()
        self.assertIn("bearer_token", schema["required"])

    def test_execute_no_token(self):
        with patch.dict('os.environ', {}, clear=True):
            result = self.plugin.execute("본문", "제목")
        self.assertFalse(result["success"])
        self.assertIn("Bearer Token", result["message"])

    @patch('services.mcp.plugins.twitter.urllib.request.urlopen')
    def test_execute_success_single_tweet(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"data": {"id": "t-123"}}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        # 짧은 콘텐츠 → 스레드 없음
        result = self.plugin.execute("짧은 본문", "제목", bearer_token="tok", as_thread=False)
        self.assertTrue(result["success"])
        self.assertIn("t-123", result["url"])

    @patch.object(TwitterPlugin, '_post_tweet')
    def test_execute_thread(self, mock_post):
        # 첫 트윗 + 스레드 2개
        mock_post.side_effect = ["t-1", "t-2", "t-3"]
        long_content = "A" * 600  # 280자 초과
        result = self.plugin.execute(long_content, "제목", bearer_token="tok", as_thread=True)
        self.assertTrue(result["success"])
        self.assertIn("t-1", result["url"])
        self.assertTrue(mock_post.call_count >= 2)

    @patch.object(TwitterPlugin, '_post_tweet', return_value='')
    def test_execute_first_tweet_fails(self, mock_post):
        result = self.plugin.execute("본문", "제목", bearer_token="tok")
        self.assertFalse(result["success"])
        self.assertIn("실패", result["message"])

    @patch('services.mcp.plugins.twitter.urllib.request.urlopen')
    def test_post_tweet_http_error(self, mock_urlopen):
        import urllib.error
        mock_err = MagicMock()
        mock_err.read.return_value = b'{"detail":"Rate limit"}'
        mock_err.code = 429
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='', code=429, msg='Too Many', hdrs=None, fp=mock_err
        )
        tweet_id = self.plugin._post_tweet("tok", "text")
        self.assertEqual(tweet_id, '')

    @patch('services.mcp.plugins.twitter.urllib.request.urlopen')
    def test_post_tweet_with_reply(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"data": {"id": "reply-1"}}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        tweet_id = self.plugin._post_tweet("tok", "reply text", reply_to_id="parent-1")
        self.assertEqual(tweet_id, "reply-1")
        # payload에 reply 필드 포함 확인
        call_args = mock_urlopen.call_args[0][0]
        body = json.loads(call_args.data.decode())
        self.assertEqual(body["reply"]["in_reply_to_tweet_id"], "parent-1")


if __name__ == '__main__':
    unittest.main()
