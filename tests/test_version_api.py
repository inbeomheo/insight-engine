"""앱 버전 API 테스트."""
import unittest

from app import create_app


class TestVersionApi(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_returns_version_info(self):
        """버전 정보 JSON 반환."""
        resp = self.client.get('/api/version')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['name'], 'Insight Engine')
        self.assertIn('version', data)
        self.assertIn('git_hash', data)
        self.assertIn('services', data)

    def test_no_auth_required(self):
        """인증 불필요."""
        resp = self.client.get('/api/version')
        self.assertEqual(resp.status_code, 200)

    def test_services_count_positive(self):
        """서비스 수가 양수."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        self.assertGreater(data['services'], 0)


if __name__ == '__main__':
    unittest.main()
