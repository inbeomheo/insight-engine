"""헬스체크 uptime 필드 테스트."""
import unittest
import time

from app import create_app


class TestHealthUptime(unittest.TestCase):
    """/health 엔드포인트의 uptime_seconds 필드 검증."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_health_has_uptime_seconds(self):
        """uptime_seconds 필드가 숫자로 존재해야 한다."""
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('uptime_seconds', data)
        self.assertIsInstance(data['uptime_seconds'], (int, float))
        self.assertGreaterEqual(data['uptime_seconds'], 0)

    def test_uptime_increases(self):
        """두 번 호출 시 uptime이 증가(또는 동일)해야 한다."""
        resp1 = self.client.get('/health')
        t1 = resp1.get_json()['uptime_seconds']
        time.sleep(0.1)
        resp2 = self.client.get('/health')
        t2 = resp2.get_json()['uptime_seconds']
        self.assertGreaterEqual(t2, t1)

    def test_health_still_returns_status(self):
        """기존 status 필드는 변함없다."""
        resp = self.client.get('/health')
        data = resp.get_json()
        self.assertEqual(data['status'], 'healthy')


if __name__ == '__main__':
    unittest.main()
