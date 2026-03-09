"""인용 신선도 알림 서비스 테스트"""
import unittest
from datetime import datetime, timezone, timedelta
from services.citation_freshness_service import (
    alert_citation_decay,
    DecayAlert,
    _calculate_age_days,
    _determine_severity,
)


class TestCalculateAgeDays(unittest.TestCase):
    """경과일 계산 테스트"""

    def test_valid_date(self):
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        age = _calculate_age_days(yesterday)
        self.assertEqual(age, 1)

    def test_iso_format_with_time(self):
        dt = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        age = _calculate_age_days(dt)
        self.assertAlmostEqual(age, 10, delta=1)

    def test_invalid_date(self):
        age = _calculate_age_days("not-a-date")
        self.assertEqual(age, -1)

    def test_future_date(self):
        future = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")
        age = _calculate_age_days(future)
        self.assertEqual(age, 0)


class TestDetermineSeverity(unittest.TestCase):
    """심각도 판단 테스트"""

    def test_critical(self):
        self.assertEqual(_determine_severity(400, 365), "critical")

    def test_warning(self):
        self.assertEqual(_determine_severity(300, 365), "warning")

    def test_info(self):
        self.assertEqual(_determine_severity(100, 365), "info")


class TestAlertCitationDecay(unittest.TestCase):
    """인용 부패 알림 테스트"""

    def test_empty_citations(self):
        result = alert_citation_decay([])
        self.assertEqual(result, [])

    def test_fresh_citation(self):
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        citations = [{"url": "https://example.com", "date": yesterday}]
        result = alert_citation_decay(citations)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].severity, "info")

    def test_old_citation_critical(self):
        old_date = (datetime.now(timezone.utc) - timedelta(days=500)).strftime("%Y-%m-%d")
        citations = [{"url": "https://old.com", "date": old_date}]
        result = alert_citation_decay(citations)
        self.assertEqual(result[0].severity, "critical")
        self.assertGreater(result[0].age_days, 365)

    def test_sorting_by_severity(self):
        now = datetime.now(timezone.utc)
        citations = [
            {"url": "https://fresh.com", "date": (now - timedelta(days=10)).strftime("%Y-%m-%d")},
            {"url": "https://old.com", "date": (now - timedelta(days=500)).strftime("%Y-%m-%d")},
            {"url": "https://mid.com", "date": (now - timedelta(days=300)).strftime("%Y-%m-%d")},
        ]
        result = alert_citation_decay(citations)
        self.assertEqual(result[0].severity, "critical")
        self.assertEqual(result[-1].severity, "info")

    def test_invalid_date_warning(self):
        citations = [{"url": "https://nodate.com", "date": "invalid"}]
        result = alert_citation_decay(citations)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].severity, "warning")
        self.assertIn("확인할 수 없습니다", result[0].recommendation)

    def test_custom_max_age(self):
        date_200_ago = (datetime.now(timezone.utc) - timedelta(days=200)).strftime("%Y-%m-%d")
        citations = [{"url": "https://test.com", "date": date_200_ago}]
        result = alert_citation_decay(citations, max_age_days=180)
        self.assertEqual(result[0].severity, "critical")

    def test_zero_max_age_defaults(self):
        """max_age_days가 0이면 365로 기본값"""
        citations = [{"url": "https://test.com", "date": "2024-01-01"}]
        result = alert_citation_decay(citations, max_age_days=0)
        self.assertIsInstance(result, list)

    def test_missing_url_skipped(self):
        citations = [{"url": "", "date": "2024-01-01"}]
        result = alert_citation_decay(citations)
        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main()
