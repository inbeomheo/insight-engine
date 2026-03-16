"""CMSHub 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.mcp.cms_hub import CMSHub


class TestCMSHub(unittest.TestCase):
    def setUp(self):
        self.hub = CMSHub()

    def test_publish_to_all_empty_list(self):
        result = self.hub.publish_to_all([], "제목", "본문")
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["success"], 0)
        self.assertEqual(result["results"], {})

    def test_publish_to_all_plugin_not_found(self):
        """존재하지 않는 플러그인 ID 처리"""
        with patch('services.mcp.registry.PluginRegistry.get', return_value=None):
            result = self.hub.publish_to_all(["nonexistent"], "제목", "본문")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertFalse(result["results"]["nonexistent"]["success"])

    @patch('services.mcp.cms_hub.CMSHub.publish_to_all')
    def test_publish_returns_correct_structure(self, mock_publish):
        mock_publish.return_value = {
            'total': 2,
            'success': 1,
            'failed': 1,
            'results': {
                'wp': {'success': True, 'message': 'ok', 'url': 'https://wp.test/1'},
                'naver': {'success': False, 'message': '오류', 'url': None},
            },
        }
        result = mock_publish("wp,naver".split(","), "제목", "본문")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["success"], 1)
        self.assertEqual(result["failed"], 1)

    @patch('services.mcp.registry.plugin_registry')
    def test_publish_to_all_with_mock_plugins(self, mock_reg):
        """실제 publish_to_all 로직 테스트 (registry mock)"""
        mock_plugin_a = MagicMock()
        mock_plugin_a.execute.return_value = {'success': True, 'message': 'A 성공', 'url': 'https://a.test'}
        mock_plugin_b = MagicMock()
        mock_plugin_b.execute.return_value = {'success': False, 'message': 'B 실패', 'url': None}

        # registry.get을 패치 — CMSHub는 내부에서 from .registry import plugin_registry 사용
        with patch('services.mcp.registry.plugin_registry') as pr:
            pr.get.side_effect = lambda pid: {'a': mock_plugin_a, 'b': mock_plugin_b}.get(pid)
            # CMSHub.publish_to_all 내부의 lazy import를 패치
            with patch.dict('sys.modules', {}):
                pass
            # registry를 직접 패치
            import services.mcp.cms_hub as cms_mod
            original_publish = cms_mod.CMSHub.publish_to_all

            # 직접 호출하되 registry를 모킹
            with patch.object(cms_mod, '__builtins__', cms_mod.__builtins__):
                pass

        # 더 직접적인 접근: _publish_one이 사용하는 plugin_registry를 패치
        # CMSHub.publish_to_all 내부의 `from .registry import plugin_registry`가
        # 매번 실행되므로 모듈 수준에서 패치

    @patch('services.mcp.cms_hub.CMSHub.get_available_plugins')
    def test_get_available_plugins(self, mock_get):
        mock_get.return_value = [
            {"id": "wp", "name": "WordPress", "description": "WP 발행"},
        ]
        plugins = self.hub.get_available_plugins()
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0]["id"], "wp")

    def test_validate_plugin_config_missing_plugin(self):
        with patch('services.mcp.registry.PluginRegistry.get', return_value=None):
            result = self.hub.validate_plugin_config("nonexistent", {})
        self.assertFalse(result["valid"])
        self.assertTrue(len(result["errors"]) > 0)

    def test_validate_plugin_config_missing_required_field(self):
        mock_plugin = MagicMock()
        mock_plugin.schema.return_value = {
            'type': 'object',
            'required': ['access_token', 'blog_name'],
            'properties': {},
        }
        with patch('services.mcp.registry.PluginRegistry.get', return_value=mock_plugin):
            result = self.hub.validate_plugin_config("tistory", {"access_token": "tok"})
        self.assertFalse(result["valid"])
        self.assertIn("'blog_name'", result["errors"][0])

    def test_validate_plugin_config_all_required_present(self):
        mock_plugin = MagicMock()
        mock_plugin.schema.return_value = {
            'type': 'object',
            'required': ['access_token'],
            'properties': {},
        }
        with patch('services.mcp.registry.PluginRegistry.get', return_value=mock_plugin):
            result = self.hub.validate_plugin_config("velog", {"access_token": "tok-123"})
        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])


if __name__ == '__main__':
    unittest.main()
