"""Shopify 발행 플러그인 라우트 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestShopifyRoutes(unittest.TestCase):
    """POST /api/mcp/plugins/shopify/publish, GET /schema 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_schema_returns_shopify_config(self, _mock_sb):
        """Shopify 스키마 엔드포인트가 설정 스키마를 반환."""
        resp = self.client.get('/api/mcp/plugins/shopify/schema',
                               headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['name'], 'Shopify Blog')
        self.assertIn('store_domain', data['schema']['properties'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_publish_missing_fields_returns_400(self, _mock_sb):
        """title/content 없이 발행 시 400."""
        resp = self.client.post('/api/mcp/plugins/shopify/publish',
                                json={'title': '제목'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.mcp.plugins.shopify.ShopifyPlugin.execute')
    def test_publish_success(self, mock_execute, _mock_sb):
        """정상 발행 시 성공 응답."""
        mock_execute.return_value = {
            'success': True,
            'message': 'Shopify Article 생성 완료',
            'url': 'https://mystore.myshopify.com/blogs/1/test',
        }
        resp = self.client.post('/api/mcp/plugins/shopify/publish',
                                json={
                                    'title': '테스트',
                                    'content': '본문',
                                    'store_domain': 'mystore.myshopify.com',
                                    'access_token': 'token123',
                                    'blog_id': '1',
                                },
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])


if __name__ == '__main__':
    unittest.main()
