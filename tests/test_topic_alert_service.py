"""
토픽 알림 서비스 단위 테스트
"""
import unittest
from services.topic_alert_service import (
    set_topic_alert,
    check_alerts,
    Alert,
)


class TestTopicAlertService(unittest.TestCase):
    """토픽 알림 서비스 단위 테스트"""

    def test_set_alert_default(self):
        """기본 알림 설정"""
        alert = set_topic_alert("AI")
        self.assertIsInstance(alert, Alert)
        self.assertEqual(alert.topic, "AI")
        self.assertEqual(alert.alert_type, "spike")
        self.assertEqual(alert.threshold, 0.5)
        self.assertFalse(alert.triggered)
        self.assertIn("AI", alert.message)

    def test_set_alert_custom_type(self):
        """커스텀 알림 유형"""
        alert = set_topic_alert("Python", threshold=0.3, alert_type="decline")
        self.assertEqual(alert.alert_type, "decline")
        self.assertEqual(alert.threshold, 0.3)

    def test_set_alert_new_entry(self):
        """신규 진입 알림"""
        alert = set_topic_alert("Rust", alert_type="new_entry", threshold=0.1)
        self.assertEqual(alert.alert_type, "new_entry")

    def test_set_alert_invalid_type(self):
        """잘못된 알림 유형 → ValueError"""
        with self.assertRaises(ValueError):
            set_topic_alert("AI", alert_type="invalid")

    def test_set_alert_invalid_threshold(self):
        """범위 초과 임계값 → ValueError"""
        with self.assertRaises(ValueError):
            set_topic_alert("AI", threshold=1.5)
        with self.assertRaises(ValueError):
            set_topic_alert("AI", threshold=-0.1)

    def test_set_alert_empty_topic(self):
        """빈 토픽 → ValueError"""
        with self.assertRaises(ValueError):
            set_topic_alert("")
        with self.assertRaises(ValueError):
            set_topic_alert("   ")

    def test_set_alert_strips_whitespace(self):
        """토픽 앞뒤 공백 제거"""
        alert = set_topic_alert("  AI  ")
        self.assertEqual(alert.topic, "AI")

    def test_check_alerts_spike_triggered(self):
        """급등 알림 트리거"""
        alerts = [set_topic_alert("AI", threshold=0.5, alert_type="spike")]
        data = {"AI": 0.8}
        results = check_alerts(alerts, data)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].triggered)
        self.assertEqual(results[0].current_value, 0.8)
        self.assertIn("급등", results[0].message)

    def test_check_alerts_spike_not_triggered(self):
        """급등 알림 미트리거"""
        alerts = [set_topic_alert("AI", threshold=0.5, alert_type="spike")]
        data = {"AI": 0.3}
        results = check_alerts(alerts, data)
        self.assertFalse(results[0].triggered)

    def test_check_alerts_decline_triggered(self):
        """하락 알림 트리거"""
        alerts = [set_topic_alert("SEO", threshold=0.3, alert_type="decline")]
        data = {"SEO": 0.2}
        results = check_alerts(alerts, data)
        self.assertTrue(results[0].triggered)
        self.assertIn("하락", results[0].message)

    def test_check_alerts_new_entry_triggered(self):
        """신규 진입 알림 트리거"""
        alerts = [set_topic_alert("Rust", alert_type="new_entry", threshold=0.1)]
        data = {"Rust": 0.5}
        results = check_alerts(alerts, data)
        self.assertTrue(results[0].triggered)
        self.assertIn("신규 진입", results[0].message)

    def test_check_alerts_new_entry_absent(self):
        """신규 진입 — 토픽 없으면 미트리거"""
        alerts = [set_topic_alert("Rust", alert_type="new_entry", threshold=0.1)]
        data = {"Python": 0.5}
        results = check_alerts(alerts, data)
        self.assertFalse(results[0].triggered)

    def test_check_alerts_multiple(self):
        """복수 알림 동시 체크"""
        alerts = [
            set_topic_alert("AI", threshold=0.5, alert_type="spike"),
            set_topic_alert("SEO", threshold=0.3, alert_type="decline"),
            set_topic_alert("Rust", alert_type="new_entry", threshold=0.1),
        ]
        data = {"AI": 0.9, "SEO": 0.1, "Python": 0.5}
        results = check_alerts(alerts, data)
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0].triggered)   # AI spike
        self.assertTrue(results[1].triggered)   # SEO decline
        self.assertFalse(results[2].triggered)  # Rust not present

    def test_check_alerts_empty_list(self):
        """빈 알림 목록"""
        results = check_alerts([], {"AI": 0.5})
        self.assertEqual(results, [])

    def test_check_alerts_missing_topic_defaults_zero(self):
        """데이터에 없는 토픽은 값 0으로 처리"""
        alerts = [set_topic_alert("없는토픽", threshold=0.5, alert_type="spike")]
        data = {}
        results = check_alerts(alerts, data)
        self.assertEqual(results[0].current_value, 0.0)
        self.assertFalse(results[0].triggered)


if __name__ == '__main__':
    unittest.main()
