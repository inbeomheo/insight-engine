"""콘텐츠 일몰 서비스 테스트"""
import unittest
from datetime import datetime

from services.content_sunset_service import (
    SunsetPlan,
    plan_sunset,
    get_urgency_label_kr,
    _categorize_age,
    _determine_urgency,
    _calculate_sunset_date,
    _build_actions,
)


class TestCategorizeAge(unittest.TestCase):
    """나이 카테고리 분류 테스트"""

    def test_fresh(self):
        """90일 미만 → fresh"""
        self.assertEqual(_categorize_age(30), "fresh")

    def test_mature(self):
        """90~180일 → mature"""
        self.assertEqual(_categorize_age(120), "mature")

    def test_aging(self):
        """180~365일 → aging"""
        self.assertEqual(_categorize_age(300), "aging")

    def test_stale(self):
        """365일+ → stale"""
        self.assertEqual(_categorize_age(730), "stale")

    def test_boundary_fresh(self):
        """경계값: 89일 → fresh"""
        self.assertEqual(_categorize_age(89), "fresh")

    def test_boundary_mature(self):
        """경계값: 90일 → mature"""
        self.assertEqual(_categorize_age(90), "mature")

    def test_zero_days(self):
        """0일 → fresh"""
        self.assertEqual(_categorize_age(0), "fresh")


class TestDetermineUrgency(unittest.TestCase):
    """긴급도 결정 테스트"""

    def test_stale_always_high(self):
        """stale → 항상 high"""
        self.assertEqual(_determine_urgency("stale", False), "high")
        self.assertEqual(_determine_urgency("stale", True), "high")

    def test_aging_with_replacement(self):
        """aging + 대체 URL → high"""
        self.assertEqual(_determine_urgency("aging", True), "high")

    def test_aging_without_replacement(self):
        """aging + 대체 없음 → medium"""
        self.assertEqual(_determine_urgency("aging", False), "medium")

    def test_fresh_always_low(self):
        """fresh → 항상 low"""
        self.assertEqual(_determine_urgency("fresh", False), "low")
        self.assertEqual(_determine_urgency("fresh", True), "low")


class TestCalculateSunsetDate(unittest.TestCase):
    """일몰 날짜 계산 테스트"""

    def test_fresh_long_grace(self):
        """fresh → 365일 유예"""
        date_str = _calculate_sunset_date(30, "fresh")
        sunset = datetime.strptime(date_str, "%Y-%m-%d")
        diff = (sunset - datetime.now()).days
        self.assertAlmostEqual(diff, 365, delta=1)

    def test_stale_short_grace(self):
        """stale → 30일 유예"""
        date_str = _calculate_sunset_date(800, "stale")
        sunset = datetime.strptime(date_str, "%Y-%m-%d")
        diff = (sunset - datetime.now()).days
        self.assertAlmostEqual(diff, 30, delta=1)

    def test_valid_date_format(self):
        """유효한 ISO 날짜 형식"""
        date_str = _calculate_sunset_date(200, "aging")
        datetime.strptime(date_str, "%Y-%m-%d")  # 파싱 실패 시 예외


class TestBuildActions(unittest.TestCase):
    """액션 목록 생성 테스트"""

    def test_fresh_single_action(self):
        """fresh → 1개 액션"""
        actions = _build_actions("fresh", None)
        self.assertEqual(len(actions), 1)
        self.assertIn("신선", actions[0])

    def test_stale_multiple_actions(self):
        """stale → 여러 액션"""
        actions = _build_actions("stale", None)
        self.assertGreater(len(actions), 1)

    def test_replacement_url_added(self):
        """대체 URL 있으면 리다이렉트 액션 추가"""
        actions = _build_actions("aging", "https://example.com/new")
        redirect_actions = [a for a in actions if "리다이렉트" in a]
        self.assertGreater(len(redirect_actions), 0)

    def test_replacement_url_none(self):
        """대체 URL 없으면 리다이렉트 없음"""
        actions = _build_actions("aging", None)
        redirect_actions = [a for a in actions if "리다이렉트" in a]
        self.assertEqual(len(redirect_actions), 0)


class TestPlanSunset(unittest.TestCase):
    """일몰 계획 통합 테스트"""

    def test_empty_content_id(self):
        """빈 ID → 에러 안내"""
        result = plan_sunset("")
        self.assertEqual(result.content_id, "")
        self.assertIn("유효한", result.actions[0])

    def test_basic_plan(self):
        """기본 계획 생성"""
        result = plan_sunset("post-123", age_days=400)
        self.assertIsInstance(result, SunsetPlan)
        self.assertEqual(result.content_id, "post-123")
        self.assertEqual(result.age_category, "stale")
        self.assertEqual(result.urgency, "high")
        self.assertGreater(len(result.actions), 0)

    def test_with_replacement_url(self):
        """대체 URL 포함"""
        result = plan_sunset("post-456", replacement_url="https://new.com/post", age_days=500)
        self.assertEqual(result.replacement_url, "https://new.com/post")
        has_redirect = any("리다이렉트" in a for a in result.actions)
        self.assertTrue(has_redirect)

    def test_fresh_content(self):
        """신선한 콘텐츠"""
        result = plan_sunset("post-789", age_days=30)
        self.assertEqual(result.age_category, "fresh")
        self.assertEqual(result.urgency, "low")

    def test_negative_age_clamped(self):
        """음수 나이 → 0으로 보정"""
        result = plan_sunset("post-000", age_days=-10)
        self.assertEqual(result.age_category, "fresh")

    def test_sunset_date_is_future(self):
        """일몰 날짜가 미래"""
        result = plan_sunset("post-101", age_days=200)
        sunset = datetime.strptime(result.sunset_date, "%Y-%m-%d")
        self.assertGreater(sunset, datetime.now())

    def test_content_id_stripped(self):
        """ID 앞뒤 공백 제거"""
        result = plan_sunset("  post-102  ", age_days=100)
        self.assertEqual(result.content_id, "post-102")

    def test_empty_replacement_url_treated_as_none(self):
        """빈 문자열 대체 URL → None 처리"""
        result = plan_sunset("post-103", replacement_url="  ", age_days=200)
        self.assertIsNone(result.replacement_url)


class TestGetUrgencyLabelKr(unittest.TestCase):
    """긴급도 한국어 라벨 테스트"""

    def test_all_labels(self):
        """모든 긴급도에 한국어 라벨 존재"""
        self.assertEqual(get_urgency_label_kr("low"), "낮음")
        self.assertEqual(get_urgency_label_kr("medium"), "보통")
        self.assertEqual(get_urgency_label_kr("high"), "높음")

    def test_unknown(self):
        """알 수 없는 값은 원문 반환"""
        self.assertEqual(get_urgency_label_kr("critical"), "critical")


if __name__ == "__main__":
    unittest.main()
