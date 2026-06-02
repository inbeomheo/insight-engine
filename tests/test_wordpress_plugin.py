"""WordPressPlugin 단위 테스트"""
import unittest
from unittest.mock import patch, Mock

from services.mcp.plugins.wordpress import WordPressPlugin


class TestWordPressPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = WordPressPlugin()

    def test_name_and_description(self):
        self.assertEqual(self.plugin.name, "WordPress")
        self.assertIn("WordPress", self.plugin.description)

    def test_schema_structure(self):
        schema = self.plugin.schema()
        self.assertEqual(schema["type"], "object")
        self.assertIn("site_url", schema["properties"])
        self.assertIn("username", schema["properties"])

    def test_execute_requires_credentials(self):
        result = self.plugin.execute("본문 내용", "테스트 제목")
        self.assertFalse(result["success"])
        self.assertIn("WordPress", result["message"])
        self.assertIsNone(result["url"])

    @patch("services.mcp.plugins.wordpress.requests.post")
    def test_execute_creates_wordpress_post(self, mock_post):
        mock_resp = Mock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 10, "link": "https://wp.test/post/10"}
        mock_post.return_value = mock_resp

        result = self.plugin.execute(
            "본문 내용",
            "테스트 제목",
            site_url="https://wp.test",
            username="admin",
            app_password="secret",
            status="draft",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["url"], "https://wp.test/post/10")
        mock_post.assert_called_once()
        url = mock_post.call_args.args[0]
        kwargs = mock_post.call_args.kwargs
        self.assertEqual(url, "https://wp.test/wp-json/wp/v2/posts")
        self.assertEqual(kwargs["json"]["title"], "테스트 제목")
        self.assertEqual(kwargs["json"]["content"], "본문 내용")
        self.assertEqual(kwargs["json"]["status"], "draft")

    def test_execute_with_kwargs(self):
        result = self.plugin.execute("본문", "제목", site_url="https://wp.test", username="admin")
        self.assertFalse(result["success"])

    def test_execute_response_structure(self):
        result = self.plugin.execute("본문", "제목")
        self.assertIn("success", result)
        self.assertIn("message", result)
        self.assertIn("url", result)


if __name__ == '__main__':
    unittest.main()
