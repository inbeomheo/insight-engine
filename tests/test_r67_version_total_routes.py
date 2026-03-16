"""R67: /api/version 응답에 total_routes 필드 테스트"""
import unittest

from app import create_app


class TestVersionTotalRoutes(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_total_routes_present(self):
        """total_routes 필드가 응답에 포함된다."""
        resp = self.client.get('/api/version')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('total_routes', data)

    def test_total_routes_is_positive_integer(self):
        """total_routes가 양의 정수이다."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        self.assertIsInstance(data['total_routes'], int)
        self.assertGreater(data['total_routes'], 0)

    def test_total_routes_greater_than_route_files(self):
        """total_routes가 라우트 파일 수 이상이다 (파일당 여러 엔드포인트)."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        self.assertGreaterEqual(data['total_routes'], data['routes'])

    def test_existing_fields_preserved(self):
        """기존 필드(name, version, services, routes)가 유지된다."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        self.assertIn('name', data)
        self.assertIn('version', data)
        self.assertIn('services', data)
        self.assertIn('routes', data)


if __name__ == '__main__':
    unittest.main()
