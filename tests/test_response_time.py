"""API 응답 시간 헤더 테스트."""
import unittest

from app import create_app


class TestResponseTimeHeader(unittest.TestCase):
    """X-Response-Time 헤더 검증."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_health_has_response_time(self):
        """GET /health에 X-Response-Time 헤더 포함."""
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)
        rt = resp.headers.get('X-Response-Time')
        self.assertIsNotNone(rt, 'X-Response-Time 헤더 없음')
        self.assertTrue(rt.endswith('ms'))

    def test_response_time_is_numeric(self):
        """응답 시간 값이 유효한 숫자."""
        resp = self.client.get('/health')
        rt = resp.headers.get('X-Response-Time', '0ms')
        ms = float(rt.replace('ms', ''))
        self.assertGreater(ms, 0)
        self.assertLess(ms, 10000)  # 10초 이내

    def test_404_also_has_response_time(self):
        """존재하지 않는 경로도 헤더 포함."""
        resp = self.client.get('/nonexistent-path-12345')
        rt = resp.headers.get('X-Response-Time')
        self.assertIsNotNone(rt)


if __name__ == '__main__':
    unittest.main()
