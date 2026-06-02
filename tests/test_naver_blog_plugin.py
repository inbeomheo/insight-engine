"""NaverBlogPlugin 단위 테스트"""
import unittest
from unittest.mock import patch, Mock

from services.mcp.plugins.naver_blog import NaverBlogPlugin


class TestNaverBlogPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = NaverBlogPlugin()

    def test_name_and_description(self):
        self.assertEqual(self.plugin.name, "네이버 블로그")
        self.assertIn("네이버", self.plugin.description)

    def test_schema_structure(self):
        schema = self.plugin.schema()
        self.assertEqual(schema["type"], "object")
        self.assertIn("blog_id", schema["properties"])

    def test_execute_requires_webhook(self):
        result = self.plugin.execute("본문 내용", "테스트 제목")
        self.assertFalse(result["success"])
        self.assertIn("웹훅", result["message"])
        self.assertIsNone(result["url"])

    @patch("services.mcp.plugins.naver_blog.requests.post")
    def test_execute_posts_to_webhook(self, mock_post):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"url": "https://blog.naver.com/my_blog/1"}
        mock_post.return_value = mock_resp

        result = self.plugin.execute(
            "본문 내용",
            "테스트 제목",
            blog_id="my_blog",
            webhook_url="https://hook.test/naver",
            category="AI",
            tags=["qa", "blog"],
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["url"], "https://blog.naver.com/my_blog/1")
        mock_post.assert_called_once()
        url = mock_post.call_args.args[0]
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(url, "https://hook.test/naver")
        self.assertEqual(payload["title"], "테스트 제목")
        self.assertEqual(payload["content"], "본문 내용")
        self.assertEqual(payload["blog_id"], "my_blog")
        self.assertEqual(payload["category"], "AI")
        self.assertEqual(payload["tags"], ["qa", "blog"])

    def test_execute_with_blog_id(self):
        result = self.plugin.execute("본문", "제목", blog_id="my_blog")
        self.assertFalse(result["success"])

    def test_execute_response_structure(self):
        result = self.plugin.execute("본문", "제목")
        self.assertIn("success", result)
        self.assertIn("message", result)
        self.assertIn("url", result)


if __name__ == '__main__':
    unittest.main()
