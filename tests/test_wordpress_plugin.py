"""WordPressPlugin 단위 테스트"""
import unittest

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

    def test_execute_returns_success_placeholder(self):
        result = self.plugin.execute("본문 내용", "테스트 제목")
        self.assertTrue(result["success"])
        self.assertIn("테스트 제목", result["message"])
        self.assertIn("API 연동", result["message"])
        self.assertIsNone(result["url"])

    def test_execute_with_kwargs(self):
        result = self.plugin.execute("본문", "제목", site_url="https://wp.test", username="admin")
        self.assertTrue(result["success"])

    def test_execute_response_structure(self):
        result = self.plugin.execute("본문", "제목")
        self.assertIn("success", result)
        self.assertIn("message", result)
        self.assertIn("url", result)


if __name__ == '__main__':
    unittest.main()
