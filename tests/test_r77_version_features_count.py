"""R77: /api/version에 features_count 필드 테스트."""
import unittest

from app import create_app


class TestVersionFeaturesCount(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_features_count_exists(self):
        """응답에 features_count 필드 포함."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        self.assertIn('features_count', data)

    def test_features_count_is_positive(self):
        """features_count가 양수."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        self.assertGreater(data['features_count'], 0)

    def test_features_count_is_integer(self):
        """features_count가 정수 타입."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        self.assertIsInstance(data['features_count'], int)

    def test_features_count_lte_total_routes(self):
        """features_count <= total_routes (API만 필터링이므로)."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        self.assertLessEqual(data['features_count'], data['total_routes'])

    def test_features_count_includes_api_endpoints(self):
        """features_count >= 10 (최소 10개 이상 API 존재)."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        self.assertGreaterEqual(data['features_count'], 10)


if __name__ == '__main__':
    unittest.main()
