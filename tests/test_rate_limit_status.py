"""
R23: /api/rate-limit/status 엔드포인트 테스트
"""
from __future__ import annotations

import unittest
from unittest.mock import patch


class TestRateLimitStatus(unittest.TestCase):
    """Rate limit 상태 조회 API 테스트"""

    def setUp(self):
        from app import create_app
        self.app = create_app()
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_returns_200(self, _):
        """정상 응답 200"""
        resp = self.client.get('/api/rate-limit/status')
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_response_structure(self, _):
        """응답에 enabled, client_ip, limits 필드 포함"""
        resp = self.client.get('/api/rate-limit/status')
        data = resp.get_json()
        self.assertIn('enabled', data)
        self.assertIn('client_ip', data)
        self.assertIn('limits', data)
        self.assertIsInstance(data['limits'], list)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_limits_contain_generate_endpoint(self, _):
        """/generate 엔드포인트가 limits에 포함"""
        resp = self.client.get('/api/rate-limit/status')
        data = resp.get_json()
        endpoints = [item['endpoint'] for item in data['limits']]
        self.assertIn('/generate', endpoints)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_limit_item_structure(self, _):
        """각 limit 항목에 endpoint, limit 필드 포함"""
        resp = self.client.get('/api/rate-limit/status')
        data = resp.get_json()
        for item in data['limits']:
            self.assertIn('endpoint', item)
            self.assertIn('limit', item)
            self.assertIsInstance(item['endpoint'], str)
            self.assertIsInstance(item['limit'], str)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_enabled_is_boolean(self, _):
        """enabled 필드는 bool 타입"""
        resp = self.client.get('/api/rate-limit/status')
        data = resp.get_json()
        self.assertIsInstance(data['enabled'], bool)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_client_ip_is_string(self, _):
        """client_ip 필드는 문자열"""
        resp = self.client.get('/api/rate-limit/status')
        data = resp.get_json()
        self.assertIsInstance(data['client_ip'], str)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_has_five_endpoints(self, _):
        """5개 엔드포인트 정보 포함"""
        resp = self.client.get('/api/rate-limit/status')
        data = resp.get_json()
        self.assertEqual(len(data['limits']), 5)


if __name__ == '__main__':
    unittest.main()
