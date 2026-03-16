"""플러그인 SDK 정보 라우트 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestPluginSDKRoutes(unittest.TestCase):
    """GET /api/mcp/sdk/info, /api/mcp/sdk/schema/<id> 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_sdk_info_returns_metadata(self, _mock_sb):
        """SDK 정보 엔드포인트가 메타데이터를 반환."""
        resp = self.client.get('/api/mcp/sdk/info', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['sdk_version'], '1.0.0')
        self.assertEqual(data['base_class'], 'PluginBase')
        self.assertIn('registered_plugins', data)
        self.assertIsInstance(data['registered_plugins'], list)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_schema_not_found_returns_404(self, _mock_sb):
        """존재하지 않는 플러그인 ID로 스키마 조회 시 404."""
        resp = self.client.get('/api/mcp/sdk/schema/nonexistent_plugin',
                               headers=_HEADERS)
        self.assertEqual(resp.status_code, 404)
        data = resp.get_json()
        self.assertIn('error', data)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.mcp.registry.plugin_registry.get')
    def test_schema_returns_plugin_info(self, mock_get, _mock_sb):
        """등록된 플러그인 ID로 스키마 조회 시 정보 반환."""
        from unittest.mock import MagicMock
        mock_plugin = MagicMock()
        mock_plugin.name = 'Test Plugin'
        mock_plugin.description = '테스트 플러그인'
        mock_plugin.schema.return_value = {'type': 'object', 'properties': {}}
        mock_get.return_value = mock_plugin

        resp = self.client.get('/api/mcp/sdk/schema/test_plugin',
                               headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['plugin_id'], 'test_plugin')
        self.assertEqual(data['name'], 'Test Plugin')
        self.assertIn('schema', data)


if __name__ == '__main__':
    unittest.main()
