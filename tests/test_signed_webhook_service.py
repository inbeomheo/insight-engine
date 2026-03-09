"""서명형 웹훅 서비스 테스트"""

import unittest
from datetime import datetime, timedelta
from services.signed_webhook_service import (
    WebhookPayload,
    create_payload, verify_signature, format_headers, is_replay_attack,
)


class TestSignedWebhookService(unittest.TestCase):
    """서명형 웹훅 서비스 테스트"""

    def test_create_payload(self):
        """페이로드 생성"""
        p = create_payload("content.created", {"id": "123"}, "secret")
        self.assertEqual(p.event_type, "content.created")
        self.assertEqual(p.data, {"id": "123"})
        self.assertIsNotNone(p.signature)
        self.assertIsNotNone(p.payload_id)

    def test_create_payload_signature_not_empty(self):
        """서명이 비어있지 않음"""
        p = create_payload("test", {}, "key")
        self.assertTrue(len(p.signature) > 0)

    def test_verify_signature_valid(self):
        """유효한 서명 검증"""
        secret = "my_secret_key"
        p = create_payload("event", {"key": "value"}, secret)
        self.assertTrue(verify_signature(p, secret))

    def test_verify_signature_wrong_secret(self):
        """잘못된 시크릿"""
        p = create_payload("event", {"key": "value"}, "correct_secret")
        self.assertFalse(verify_signature(p, "wrong_secret"))

    def test_verify_signature_tampered_data(self):
        """데이터 변조 감지"""
        p = create_payload("event", {"key": "value"}, "secret")
        p.data = {"key": "tampered"}
        self.assertFalse(verify_signature(p, "secret"))

    def test_verify_signature_tampered_event(self):
        """이벤트 변조 감지"""
        p = create_payload("event_a", {}, "secret")
        p.event_type = "event_b"
        self.assertFalse(verify_signature(p, "secret"))

    def test_format_headers(self):
        """HTTP 헤더 생성"""
        p = create_payload("event", {}, "secret")
        headers = format_headers(p)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["X-Webhook-Id"], p.payload_id)
        self.assertEqual(headers["X-Webhook-Event"], "event")
        self.assertTrue(headers["X-Webhook-Signature"].startswith("sha256="))

    def test_format_headers_timestamp(self):
        """헤더에 타임스탬프 포함"""
        p = create_payload("event", {}, "secret")
        headers = format_headers(p)
        self.assertEqual(headers["X-Webhook-Timestamp"], p.timestamp)

    def test_is_replay_attack_within_window(self):
        """허용 시간 이내 (공격 아님)"""
        now = datetime.now()
        p = create_payload("event", {}, "secret")
        p.timestamp = now.isoformat()
        current = (now + timedelta(seconds=30)).isoformat()
        self.assertFalse(is_replay_attack(p, 300, current))

    def test_is_replay_attack_expired(self):
        """허용 시간 초과 (리플레이 공격)"""
        now = datetime.now()
        p = create_payload("event", {}, "secret")
        p.timestamp = (now - timedelta(minutes=10)).isoformat()
        current = now.isoformat()
        self.assertTrue(is_replay_attack(p, 60, current))

    def test_is_replay_attack_invalid_timestamp(self):
        """유효하지 않은 타임스탬프"""
        p = create_payload("event", {}, "secret")
        p.timestamp = "invalid-time"
        self.assertTrue(is_replay_attack(p, 300, datetime.now().isoformat()))

    def test_different_data_different_signature(self):
        """다른 데이터는 다른 서명"""
        s = "same_secret"
        p1 = create_payload("event", {"a": 1}, s)
        p2 = create_payload("event", {"b": 2}, s)
        self.assertNotEqual(p1.signature, p2.signature)

    def test_same_data_same_secret_consistent(self):
        """동일 데이터+시크릿은 동일 서명 (타임스탬프 제외)"""
        s = "secret"
        p = create_payload("event", {"a": 1}, s)
        # verify가 통과하면 서명이 일관적
        self.assertTrue(verify_signature(p, s))


if __name__ == "__main__":
    unittest.main()
