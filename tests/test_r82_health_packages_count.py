"""R82: /api/health/detailed에 python_packages_count 필드 추가 테스트"""
import unittest
from unittest.mock import patch

from app import create_app


class TestHealthPackagesCount(unittest.TestCase):
    """/api/health/detailed 응답의 python_packages_count 필드 검증"""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_python_packages_count_present(self, _mock_sb):
        """응답에 python_packages_count 필드가 존재"""
        resp = self.client.get('/api/health/detailed')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('python_packages_count', data['checks'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_python_packages_count_is_positive_int(self, _mock_sb):
        """python_packages_count가 양의 정수"""
        resp = self.client.get('/api/health/detailed')
        data = resp.get_json()
        count = data['checks']['python_packages_count']
        self.assertIsInstance(count, int)
        self.assertGreater(count, 0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_existing_fields_preserved(self, _mock_sb):
        """기존 필드들이 유지됨"""
        resp = self.client.get('/api/health/detailed')
        data = resp.get_json()
        checks = data['checks']
        self.assertIn('providers', checks)
        self.assertIn('supabase', checks)
        self.assertIn('services', checks)
        self.assertIn('active_requests', checks)


if __name__ == '__main__':
    unittest.main()
