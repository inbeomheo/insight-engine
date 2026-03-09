"""샌드박스 데모 서비스 테스트"""

import unittest
from datetime import datetime, timedelta
from services.sandbox_demo_service import (
    SandboxConfig, SandboxSession,
    create_sandbox, validate_request, get_usage_stats,
)


class TestSandboxDemoService(unittest.TestCase):
    """샌드박스 데모 서비스 테스트"""

    def test_create_sandbox_basic(self):
        """기본 샌드박스 생성"""
        session = create_sandbox(["/api/generate"], rate_limit=5, ttl=15)
        self.assertFalse(session.is_expired)
        self.assertEqual(session.request_count, 0)
        self.assertEqual(session.config.rate_limit, 5)

    def test_create_sandbox_empty_endpoints(self):
        """빈 엔드포인트 거부"""
        with self.assertRaises(ValueError):
            create_sandbox([])

    def test_create_sandbox_invalid_rate_limit(self):
        """0 이하 rate_limit 거부"""
        with self.assertRaises(ValueError):
            create_sandbox(["/api"], rate_limit=0)

    def test_create_sandbox_invalid_ttl(self):
        """0 이하 TTL 거부"""
        with self.assertRaises(ValueError):
            create_sandbox(["/api"], ttl=0)

    def test_validate_request_allowed(self):
        """유효한 요청"""
        session = create_sandbox(["/api/generate"], rate_limit=10, ttl=30)
        result = validate_request(session, "/api/generate")
        self.assertTrue(result["allowed"])
        self.assertEqual(session.request_count, 1)

    def test_validate_request_wrong_endpoint(self):
        """허용되지 않은 엔드포인트"""
        session = create_sandbox(["/api/generate"], rate_limit=10, ttl=30)
        result = validate_request(session, "/api/admin")
        self.assertFalse(result["allowed"])
        self.assertIn("허용되지 않은", result["reason"])

    def test_validate_request_rate_exceeded(self):
        """속도 제한 초과"""
        session = create_sandbox(["/api/generate"], rate_limit=2, ttl=30)
        validate_request(session, "/api/generate")
        validate_request(session, "/api/generate")
        result = validate_request(session, "/api/generate")
        self.assertFalse(result["allowed"])
        self.assertIn("속도 제한", result["reason"])

    def test_validate_request_expired(self):
        """세션 만료"""
        session = create_sandbox(["/api/generate"], rate_limit=10, ttl=5)
        # 10분 후 시간 전달
        future = (datetime.now() + timedelta(minutes=10)).isoformat()
        result = validate_request(session, "/api/generate", current_time=future)
        self.assertFalse(result["allowed"])
        self.assertTrue(session.is_expired)

    def test_validate_request_remaining_count(self):
        """남은 요청 수"""
        session = create_sandbox(["/api/generate"], rate_limit=5, ttl=30)
        result = validate_request(session, "/api/generate")
        self.assertEqual(result["remaining"], 4)

    def test_get_usage_stats(self):
        """사용량 통계"""
        session = create_sandbox(["/api/generate"], rate_limit=10, ttl=30)
        validate_request(session, "/api/generate")
        validate_request(session, "/api/generate")
        stats = get_usage_stats(session)
        self.assertEqual(stats["request_count"], 2)
        self.assertEqual(stats["remaining"], 8)
        self.assertFalse(stats["is_expired"])

    def test_get_usage_stats_empty(self):
        """초기 통계"""
        session = create_sandbox(["/api/test"], rate_limit=5, ttl=10)
        stats = get_usage_stats(session)
        self.assertEqual(stats["request_count"], 0)
        self.assertEqual(stats["remaining"], 5)

    def test_validate_request_increments(self):
        """요청마다 카운트 증가"""
        session = create_sandbox(["/api/test"], rate_limit=10, ttl=30)
        for i in range(3):
            validate_request(session, "/api/test")
        self.assertEqual(session.request_count, 3)

    def test_expired_session_blocks_all(self):
        """만료된 세션은 모든 요청 차단"""
        session = create_sandbox(["/api/test"], rate_limit=10, ttl=1)
        session.is_expired = True
        result = validate_request(session, "/api/test")
        self.assertFalse(result["allowed"])


if __name__ == "__main__":
    unittest.main()
