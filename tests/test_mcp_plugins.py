"""
MCP 플러그인 시스템 테스트

레지스트리 등록/조회, 플러그인 실행, API 엔드포인트를 검증합니다.
"""
import unittest
from unittest.mock import patch

from services.mcp.registry import PluginRegistry
from services.mcp.plugin_interface import MCPPlugin
from services.mcp.plugins.naver_blog import NaverBlogPlugin
from services.mcp.plugins.wordpress import WordPressPlugin


class DummyPlugin(MCPPlugin):
    """테스트용 더미 플러그인"""

    @property
    def name(self) -> str:
        return "더미"

    @property
    def description(self) -> str:
        return "테스트용 플러그인"

    def schema(self) -> dict:
        return {"type": "object", "properties": {}}

    def execute(self, content: str, title: str, **kwargs) -> dict:
        return {"success": True, "message": f"더미 발행: {title}", "url": None}


class TestPluginRegistry(unittest.TestCase):
    """레지스트리 등록/조회 테스트"""

    def setUp(self):
        self.registry = PluginRegistry()

    def test_register_and_get(self):
        """플러그인 등록 후 조회"""
        plugin = DummyPlugin()
        self.registry.register('dummy', plugin)
        self.assertIs(self.registry.get('dummy'), plugin)

    def test_get_unregistered_returns_none(self):
        """미등록 플러그인 조회 시 None"""
        self.assertIsNone(self.registry.get('nonexistent'))

    def test_list_plugins(self):
        """플러그인 목록 반환"""
        self.registry.register('dummy', DummyPlugin())
        plugins = self.registry.list_plugins()
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0]['id'], 'dummy')
        self.assertEqual(plugins[0]['name'], '더미')
        self.assertEqual(plugins[0]['description'], '테스트용 플러그인')

    def test_list_plugins_empty(self):
        """빈 레지스트리 목록"""
        self.assertEqual(self.registry.list_plugins(), [])

    def test_execute_success(self):
        """플러그인 실행 성공"""
        self.registry.register('dummy', DummyPlugin())
        result = self.registry.execute('dummy', '콘텐츠 본문', '테스트 제목')
        self.assertTrue(result['success'])
        self.assertIn('테스트 제목', result['message'])

    def test_execute_unregistered_plugin(self):
        """미등록 플러그인 실행 시 에러 응답"""
        result = self.registry.execute('nonexistent', '콘텐츠', '제목')
        self.assertFalse(result['success'])
        self.assertIn('nonexistent', result['message'])


class TestNaverBlogPlugin(unittest.TestCase):
    """네이버 블로그 플러그인 테스트"""

    def test_properties(self):
        plugin = NaverBlogPlugin()
        self.assertEqual(plugin.name, "네이버 블로그")
        self.assertIsInstance(plugin.description, str)

    def test_schema(self):
        plugin = NaverBlogPlugin()
        schema = plugin.schema()
        self.assertEqual(schema['type'], 'object')
        self.assertIn('blog_id', schema['properties'])

    def test_execute_placeholder(self):
        plugin = NaverBlogPlugin()
        result = plugin.execute('본문', '테스트 글')
        self.assertTrue(result['success'])
        self.assertIn('테스트 글', result['message'])


class TestWordPressPlugin(unittest.TestCase):
    """WordPress 플러그인 테스트"""

    def test_properties(self):
        plugin = WordPressPlugin()
        self.assertEqual(plugin.name, "WordPress")
        self.assertIsInstance(plugin.description, str)

    def test_schema(self):
        plugin = WordPressPlugin()
        schema = plugin.schema()
        self.assertEqual(schema['type'], 'object')
        self.assertIn('site_url', schema['properties'])

    def test_execute_placeholder(self):
        plugin = WordPressPlugin()
        result = plugin.execute('본문', '테스트 포스트')
        self.assertTrue(result['success'])
        self.assertIn('테스트 포스트', result['message'])


class TestMcpApiEndpoints(unittest.TestCase):
    """MCP API 엔드포인트 테스트"""

    def setUp(self):
        from app import create_app
        self.app = create_app({'TESTING': True})
        self.client = self.app.test_client()

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_list_plugins(self, _):
        """GET /api/mcp/plugins — 플러그인 목록 반환"""
        res = self.client.get('/api/mcp/plugins')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('plugins', data)
        ids = [p['id'] for p in data['plugins']]
        self.assertIn('naver_blog', ids)
        self.assertIn('wordpress', ids)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_publish_success(self, _):
        """POST /api/mcp/publish — 발행 성공"""
        res = self.client.post('/api/mcp/publish', json={
            'plugin_id': 'naver_blog',
            'title': '테스트 제목',
            'content': '테스트 콘텐츠',
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_publish_missing_fields(self, _):
        """POST /api/mcp/publish — 필수 필드 누락 시 400"""
        res = self.client.post('/api/mcp/publish', json={
            'plugin_id': 'naver_blog',
        })
        self.assertEqual(res.status_code, 400)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_publish_unknown_plugin(self, _):
        """POST /api/mcp/publish — 미등록 플러그인 시 404"""
        res = self.client.post('/api/mcp/publish', json={
            'plugin_id': 'unknown',
            'title': '제목',
            'content': '본문',
        })
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertFalse(data['success'])

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_publish_no_body(self, _):
        """POST /api/mcp/publish — 빈 요청 시 400"""
        res = self.client.post('/api/mcp/publish',
                               data='',
                               content_type='application/json')
        self.assertEqual(res.status_code, 400)


if __name__ == '__main__':
    unittest.main()
