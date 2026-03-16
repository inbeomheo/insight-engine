"""R80: /api/health에 api_version 필드 테스트."""
import unittest

from app import create_app


class TestHealthApiVersion(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_health_has_api_version(self):
        """헬스체크 응답에 api_version 필드가 포함된다."""
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('api_version', data)

    def test_api_version_is_v2(self):
        """api_version 값은 'v2.0'이다."""
        resp = self.client.get('/health')
        data = resp.get_json()
        self.assertEqual(data['api_version'], 'v2.0')

    def test_health_still_has_status(self):
        """기존 status 필드가 여전히 존재한다."""
        resp = self.client.get('/health')
        data = resp.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('uptime_seconds', data)
        self.assertIn('environment', data)


if __name__ == '__main__':
    unittest.main()
