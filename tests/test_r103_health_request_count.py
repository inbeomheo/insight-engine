"""R103: /health에 request_count 필드 추가 테스트"""
import unittest

from app import create_app


class TestHealthRequestCount(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_health_has_request_count(self):
        """헬스체크 응답에 request_count 필드가 있다."""
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('request_count', data)
        self.assertIsInstance(data['request_count'], int)

    def test_request_count_increments(self):
        """연속 호출 시 request_count가 증가한다."""
        # 카운터 리셋을 위해 모듈 변수 직접 조작
        import routes.utility_routes as ur
        ur._total_request_count = 0

        resp1 = self.client.get('/health')
        count1 = resp1.get_json()['request_count']

        resp2 = self.client.get('/health')
        count2 = resp2.get_json()['request_count']

        self.assertEqual(count2, count1 + 1)

    def test_request_count_is_non_negative(self):
        """request_count는 0 이상이다."""
        resp = self.client.get('/health')
        data = resp.get_json()
        self.assertGreaterEqual(data['request_count'], 0)

    def test_existing_fields_preserved(self):
        """기존 필드(status, uptime_seconds, environment, api_version)가 유지된다."""
        resp = self.client.get('/health')
        data = resp.get_json()
        for field in ('status', 'uptime_seconds', 'environment', 'api_version', 'request_count'):
            self.assertIn(field, data)


if __name__ == '__main__':
    unittest.main()
