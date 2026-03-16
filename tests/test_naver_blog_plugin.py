"""NaverBlogPlugin 단위 테스트"""
import unittest

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

    def test_execute_returns_success_placeholder(self):
        result = self.plugin.execute("본문 내용", "테스트 제목")
        self.assertTrue(result["success"])
        self.assertIn("테스트 제목", result["message"])
        self.assertIn("API 연동", result["message"])
        self.assertIsNone(result["url"])

    def test_execute_with_blog_id(self):
        result = self.plugin.execute("본문", "제목", blog_id="my_blog")
        self.assertTrue(result["success"])

    def test_execute_response_structure(self):
        result = self.plugin.execute("본문", "제목")
        self.assertIn("success", result)
        self.assertIn("message", result)
        self.assertIn("url", result)


if __name__ == '__main__':
    unittest.main()
