"""ContentPreviewApp 단위 테스트"""
import unittest

from services.mcp.apps.content_preview import ContentPreviewApp, _text_to_html


class TestContentPreviewApp(unittest.TestCase):
    def setUp(self):
        self.app = ContentPreviewApp()

    # --- 기본 속성 ---
    def test_get_name(self):
        self.assertEqual(self.app.get_name(), "content_preview")

    def test_get_description(self):
        desc = self.app.get_description()
        self.assertTrue(len(desc) > 0)

    # --- render() ---
    def test_render_default_platform(self):
        result = self.app.render({"title": "테스트 제목", "html": "<p>본문</p>"})
        self.assertIn("네이버 블로그", result["html"])
        self.assertIn("테스트 제목", result["html"])
        self.assertIn("<p>본문</p>", result["html"])
        # 기본 플랫폼(naver_blog) 제외한 3개 액션
        self.assertEqual(len(result["actions"]), 3)

    def test_render_wordpress_platform(self):
        result = self.app.render({"title": "WP 테스트", "html": "<p>wp</p>", "platform": "wordpress"})
        self.assertIn("WordPress", result["html"])
        self.assertIn("Georgia", result["html"])

    def test_render_unknown_platform_falls_back_to_default(self):
        result = self.app.render({"title": "제목", "html": "<p>x</p>", "platform": "unknown_cms"})
        self.assertIn("네이버 블로그", result["html"])

    def test_render_no_title_shows_placeholder(self):
        result = self.app.render({"html": "<p>내용</p>"})
        self.assertIn("제목 없음", result["html"])

    def test_render_content_fallback_when_no_html(self):
        result = self.app.render({"title": "제목", "content": "텍스트 본문"})
        self.assertIn("텍스트 본문", result["html"])

    def test_render_escapes_title(self):
        result = self.app.render({"title": "<script>alert(1)</script>", "html": "<p>ok</p>"})
        self.assertNotIn("<script>", result["html"])
        self.assertIn("&lt;script&gt;", result["html"])

    def test_render_exception_returns_error_html(self):
        """render 내부에서 예외 발생 시 에러 HTML 반환"""
        result = self.app.render(None)  # _render_internal에서 AttributeError 발생
        self.assertIn("미리보기 생성 실패", result["html"])
        self.assertEqual(result["actions"], [])

    # --- handle_action() ---
    def test_handle_action_switch_platform_valid(self):
        result = self.app.handle_action("switch_platform:tistory", {})
        self.assertTrue(result["success"])
        self.assertIn("티스토리", result["message"])
        self.assertEqual(result["updated_content"], {"platform": "tistory"})

    def test_handle_action_switch_platform_invalid(self):
        result = self.app.handle_action("switch_platform:notion", {})
        self.assertFalse(result["success"])
        self.assertIn("지원하지 않는", result["message"])

    def test_handle_action_unknown(self):
        result = self.app.handle_action("delete_post", {})
        self.assertFalse(result["success"])
        self.assertIn("알 수 없는 액션", result["message"])


class TestTextToHtml(unittest.TestCase):
    def test_empty_text(self):
        self.assertIn("내용이 없습니다", _text_to_html(""))

    def test_whitespace_only(self):
        self.assertIn("내용이 없습니다", _text_to_html("   \n\n   "))

    def test_single_paragraph(self):
        self.assertEqual(_text_to_html("안녕하세요"), "<p>안녕하세요</p>")

    def test_multiple_paragraphs(self):
        html = _text_to_html("단락1\n\n단락2\n\n단락3")
        self.assertEqual(html, "<p>단락1</p><p>단락2</p><p>단락3</p>")

    def test_escapes_html(self):
        html = _text_to_html("<b>bold</b>")
        self.assertNotIn("<b>", html)
        self.assertIn("&lt;b&gt;", html)


if __name__ == '__main__':
    unittest.main()
