"""
MCP Apps 통합 테스트

P4-29E: ContentPreviewApp, InlineEditorApp, API 라우트를 검증합니다.
"""
import unittest
from unittest.mock import patch


# ── 단위 테스트: BaseMCPApp / MCPAppRegistry ─────────────────────────

class TestMCPAppRegistry(unittest.TestCase):
    """MCPAppRegistry 등록/조회 기능 테스트"""

    def setUp(self):
        from services.mcp.mcp_apps import MCPAppRegistry, BaseMCPApp

        class _DummyApp(BaseMCPApp):
            def get_name(self): return "dummy"
            def get_description(self): return "테스트 앱"
            def render(self, content): return {"html": "<p>ok</p>", "actions": []}
            def handle_action(self, action, data): return {"success": True, "message": "ok", "updated_content": None}

        self.registry = MCPAppRegistry()
        self.dummy = _DummyApp()

    def test_register_and_get(self):
        self.registry.register(self.dummy)
        found = self.registry.get("dummy")
        self.assertIsNotNone(found)
        self.assertEqual(found.get_name(), "dummy")

    def test_get_missing_returns_none(self):
        self.assertIsNone(self.registry.get("nonexistent"))

    def test_list_apps(self):
        self.registry.register(self.dummy)
        apps = self.registry.list_apps()
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0]["name"], "dummy")
        self.assertEqual(apps[0]["description"], "테스트 앱")


# ── 단위 테스트: ContentPreviewApp ─────────────────────────────────

class TestContentPreviewApp(unittest.TestCase):
    """콘텐츠 미리보기 앱 렌더링 테스트"""

    def setUp(self):
        from services.mcp.apps.content_preview import ContentPreviewApp
        self.app = ContentPreviewApp()

    def test_get_name(self):
        self.assertEqual(self.app.get_name(), "content_preview")

    def test_render_returns_html_and_actions(self):
        content = {
            "title": "테스트 제목",
            "content": "첫 번째 단락\n\n두 번째 단락",
        }
        result = self.app.render(content)
        self.assertIn("html", result)
        self.assertIn("actions", result)
        self.assertIn("테스트 제목", result["html"])

    def test_render_default_platform_naver(self):
        result = self.app.render({"title": "T", "content": "C"})
        self.assertIn("네이버 블로그", result["html"])

    def test_render_wordpress_platform(self):
        result = self.app.render({"title": "T", "content": "C", "platform": "wordpress"})
        self.assertIn("WordPress", result["html"])

    def test_render_unknown_platform_falls_back(self):
        # 알 수 없는 플랫폼은 기본값(naver_blog)으로 폴백
        result = self.app.render({"title": "T", "content": "C", "platform": "unknown"})
        self.assertIn("html", result)

    def test_handle_action_switch_platform(self):
        result = self.app.handle_action("switch_platform:wordpress", {})
        self.assertTrue(result["success"])
        self.assertEqual(result["updated_content"]["platform"], "wordpress")

    def test_handle_action_invalid_platform(self):
        result = self.app.handle_action("switch_platform:nonexistent", {})
        self.assertFalse(result["success"])

    def test_handle_action_unknown(self):
        result = self.app.handle_action("do_nothing", {})
        self.assertFalse(result["success"])


# ── 단위 테스트: InlineEditorApp ───────────────────────────────────

class TestInlineEditorApp(unittest.TestCase):
    """인라인 편집 앱 테스트"""

    def setUp(self):
        from services.mcp.apps.inline_editor import InlineEditorApp
        self.app = InlineEditorApp()
        self.content = {
            "title": "편집 테스트",
            "content": "첫 번째 단락\n\n두 번째 단락\n\n세 번째 단락",
        }

    def _render_and_get_session(self):
        result = self.app.render(self.content)
        # 세션 ID는 HTML에 포함됨
        import re
        m = re.search(r"세션 ID: ([a-f0-9]+)", result["html"])
        return m.group(1) if m else None

    def test_get_name(self):
        self.assertEqual(self.app.get_name(), "inline_editor")

    def test_render_returns_html_and_actions(self):
        result = self.app.render(self.content)
        self.assertIn("html", result)
        self.assertIn("actions", result)
        self.assertTrue(len(result["actions"]) > 0)

    def test_render_shows_sections(self):
        result = self.app.render(self.content)
        # 3개 단락 모두 포함되어야 함
        self.assertIn("단락 1", result["html"])
        self.assertIn("단락 2", result["html"])
        self.assertIn("단락 3", result["html"])

    def test_save_edit_action(self):
        session_id = self._render_and_get_session()
        self.assertIsNotNone(session_id)

        result = self.app.handle_action("save_edit", {
            "session_id": session_id,
            "section": 0,
            "new_content": "수정된 첫 번째 단락",
        })
        self.assertTrue(result["success"])
        self.assertEqual(result["updated_content"]["sections"][0], "수정된 첫 번째 단락")

    def test_undo_action(self):
        session_id = self._render_and_get_session()
        # 편집 후 undo
        self.app.handle_action("save_edit", {
            "session_id": session_id, "section": 1, "new_content": "변경됨"
        })
        result = self.app.handle_action("undo", {"session_id": session_id})
        self.assertTrue(result["success"])
        # 원본으로 복원
        self.assertEqual(result["updated_content"]["sections"][1], "두 번째 단락")

    def test_undo_with_no_history(self):
        session_id = self._render_and_get_session()
        result = self.app.handle_action("undo", {"session_id": session_id})
        self.assertFalse(result["success"])

    def test_reset_action(self):
        session_id = self._render_and_get_session()
        self.app.handle_action("save_edit", {
            "session_id": session_id, "section": 0, "new_content": "변경됨"
        })
        result = self.app.handle_action("reset", {
            "session_id": session_id,
            "original_content": "리셋 단락",
        })
        self.assertTrue(result["success"])
        self.assertEqual(result["updated_content"]["sections"][0], "리셋 단락")

    def test_get_result_action(self):
        session_id = self._render_and_get_session()
        result = self.app.handle_action("get_result", {"session_id": session_id})
        self.assertTrue(result["success"])
        self.assertIn("content", result["updated_content"])
        self.assertIn("첫 번째 단락", result["updated_content"]["content"])

    def test_invalid_session_id(self):
        result = self.app.handle_action("save_edit", {
            "session_id": "nonexistent",
            "section": 0,
            "new_content": "X",
        })
        self.assertFalse(result["success"])

    def test_save_edit_out_of_range(self):
        session_id = self._render_and_get_session()
        result = self.app.handle_action("save_edit", {
            "session_id": session_id,
            "section": 999,
            "new_content": "X",
        })
        self.assertFalse(result["success"])


# ── API 라우트 테스트 ──────────────────────────────────────────────

class TestMCPAppsRoutes(unittest.TestCase):
    """MCP Apps API 엔드포인트 테스트"""

    def setUp(self):
        from app import create_app
        self.app_ctx = create_app({'TESTING': True})
        self.client = self.app_ctx.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_list_apps(self, _mock):
        res = self.client.get('/api/mcp-apps')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("apps", data)
        app_names = [a["name"] for a in data["apps"]]
        self.assertIn("content_preview", app_names)
        self.assertIn("inline_editor", app_names)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_render_content_preview(self, _mock):
        res = self.client.post('/api/mcp-apps/content_preview/render', json={
            "title": "API 테스트",
            "content": "테스트 내용",
            "platform": "naver_blog",
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("html", data)
        self.assertIn("actions", data)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_render_inline_editor(self, _mock):
        res = self.client.post('/api/mcp-apps/inline_editor/render', json={
            "title": "편집 테스트",
            "content": "단락 1\n\n단락 2",
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("html", data)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_render_unknown_app(self, _mock):
        res = self.client.post('/api/mcp-apps/nonexistent/render', json={"title": "T"})
        self.assertEqual(res.status_code, 404)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_action_switch_platform(self, _mock):
        res = self.client.post('/api/mcp-apps/content_preview/action', json={
            "action": "switch_platform:wordpress",
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_action_missing_action_field(self, _mock):
        res = self.client.post('/api/mcp-apps/content_preview/action', json={})
        self.assertEqual(res.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_action_unknown_app(self, _mock):
        res = self.client.post('/api/mcp-apps/nonexistent/action', json={"action": "noop"})
        self.assertEqual(res.status_code, 404)


if __name__ == '__main__':
    unittest.main()
