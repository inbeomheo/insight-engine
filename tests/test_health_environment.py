"""R56: /health 엔드포인트 environment 필드 테스트"""
import unittest


class TestHealthEnvironment(unittest.TestCase):
    """/health 응답에 environment 필드 검증"""

    def setUp(self):
        from app import create_app
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_has_environment_field(self):
        """environment 필드가 존재해야 한다"""
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('environment', data)

    def test_environment_is_valid_value(self):
        """environment는 development 또는 production"""
        resp = self.client.get('/health')
        data = resp.get_json()
        self.assertIn(data['environment'], ['development', 'production'])

    def test_debug_mode_returns_development(self):
        """debug=True이면 development"""
        self.app.debug = True
        resp = self.client.get('/health')
        data = resp.get_json()
        self.assertEqual(data['environment'], 'development')

    def test_existing_fields_preserved(self):
        """기존 status, uptime_seconds 필드 유지"""
        resp = self.client.get('/health')
        data = resp.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('uptime_seconds', data)


if __name__ == '__main__':
    unittest.main()
