"""R100: /api/version 응답에 total_tests 필드 포함 테스트."""
import unittest

from app import create_app


class TestVersionTotalTests(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_total_tests_in_response(self):
        """total_tests 필드가 응답에 포함된다."""
        resp = self.client.get('/api/version')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('total_tests', data)

    def test_total_tests_is_positive(self):
        """total_tests는 양수 (테스트 파일이 존재하므로)."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        self.assertGreater(data['total_tests'], 0)

    def test_total_tests_is_integer(self):
        """total_tests는 정수 타입이다."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        self.assertIsInstance(data['total_tests'], int)


if __name__ == '__main__':
    unittest.main()
