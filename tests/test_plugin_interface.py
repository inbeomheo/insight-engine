"""plugin_interface 단위 테스트 — 추상 클래스 서브클래싱 검증"""
import unittest

from services.mcp.plugin_interface import MCPPlugin


class DummyPlugin(MCPPlugin):
    """테스트용 구체 구현"""

    @property
    def name(self) -> str:
        return "DummyPlugin"

    @property
    def description(self) -> str:
        return "테스트 전용 플러그인"

    def schema(self) -> dict:
        return {"type": "object", "properties": {"api_key": {"type": "string"}}}

    def execute(self, content: str, title: str, **kwargs) -> dict:
        return {"success": True, "message": "published", "url": "https://example.com/1"}


class TestMCPPluginInterface(unittest.TestCase):
    """MCPPlugin 추상 인터페이스 검증"""

    def test_cannot_instantiate_abstract(self):
        with self.assertRaises(TypeError):
            MCPPlugin()

    def test_subclass_properties(self):
        plugin = DummyPlugin()
        self.assertEqual(plugin.name, "DummyPlugin")
        self.assertEqual(plugin.description, "테스트 전용 플러그인")

    def test_schema_returns_dict(self):
        plugin = DummyPlugin()
        schema = plugin.schema()
        self.assertIsInstance(schema, dict)
        self.assertIn("properties", schema)

    def test_execute_returns_success(self):
        plugin = DummyPlugin()
        result = plugin.execute("content body", "Title")
        self.assertTrue(result['success'])
        self.assertIn('url', result)


class TestIncompletePlugin(unittest.TestCase):
    def test_missing_execute_raises(self):
        """추상 메서드 미구현 시 TypeError 발생 확인"""

        class IncompletePlugin(MCPPlugin):
            @property
            def name(self) -> str:
                return "Incomplete"

            @property
            def description(self) -> str:
                return "desc"

            def schema(self) -> dict:
                return {}

            # execute 미구현

        with self.assertRaises(TypeError):
            IncompletePlugin()


if __name__ == '__main__':
    unittest.main()
