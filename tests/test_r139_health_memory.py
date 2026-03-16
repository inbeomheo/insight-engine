"""R139: /health 응답에 memory_usage_mb 필드 테스트"""
import unittest

from app import create_app


class TestHealthMemoryUsage(unittest.TestCase):
    """/health 엔드포인트의 memory_usage_mb 필드 검증."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_health_has_memory_usage_mb(self):
        """memory_usage_mb 필드가 응답에 존재해야 한다."""
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('memory_usage_mb', data)

    def test_memory_usage_is_number_or_null(self):
        """memory_usage_mb는 숫자(float/int) 또는 null이어야 한다."""
        resp = self.client.get('/health')
        data = resp.get_json()
        mem = data['memory_usage_mb']
        if mem is not None:
            self.assertIsInstance(mem, (int, float))
            self.assertGreater(mem, 0, "메모리 사용량은 0보다 커야 한다")

    def test_memory_usage_reasonable_range(self):
        """memory_usage_mb가 합리적 범위(1~10000 MB) 내여야 한다."""
        resp = self.client.get('/health')
        data = resp.get_json()
        mem = data['memory_usage_mb']
        if mem is not None:
            self.assertGreater(mem, 1, "프로세스 메모리가 1MB 미만은 비현실적")
            self.assertLess(mem, 10000, "프로세스 메모리가 10GB 초과는 비현실적")

    def test_other_fields_still_present(self):
        """memory_usage_mb 추가로 기존 필드가 사라지면 안 된다."""
        resp = self.client.get('/health')
        data = resp.get_json()
        for field in ['status', 'uptime_seconds', 'environment', 'api_version']:
            self.assertIn(field, data, f"기존 필드 {field} 누락")


if __name__ == '__main__':
    unittest.main()
