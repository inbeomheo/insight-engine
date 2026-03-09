"""발행 속도 거버너 서비스 테스트"""
import unittest

from services.velocity_governor_service import (
    VelocityRecommendation,
    calculate_velocity,
    _get_subscriber_multiplier,
    _engagement_adjustment,
    _growth_adjustment,
    _clamp,
    _determine_adjustment,
)


class TestGetSubscriberMultiplier(unittest.TestCase):
    """구독자 배수 테스트"""

    def test_large_channel(self):
        """10만+ → 1.3배"""
        self.assertEqual(_get_subscriber_multiplier(200_000), 1.3)

    def test_medium_channel(self):
        """1만+ → 1.1배"""
        self.assertEqual(_get_subscriber_multiplier(15_000), 1.1)

    def test_small_channel(self):
        """1천+ → 1.0배"""
        self.assertEqual(_get_subscriber_multiplier(3_000), 1.0)

    def test_tiny_channel(self):
        """1천 미만 → 0.8배"""
        self.assertEqual(_get_subscriber_multiplier(500), 0.8)

    def test_zero_subscribers(self):
        """0명 → 0.8배"""
        self.assertEqual(_get_subscriber_multiplier(0), 0.8)


class TestEngagementAdjustment(unittest.TestCase):
    """참여율 조정 테스트"""

    def test_very_high_engagement(self):
        """10%+ → +0.2"""
        self.assertEqual(_engagement_adjustment(15.0), 0.2)

    def test_good_engagement(self):
        """5~10% → +0.1"""
        self.assertEqual(_engagement_adjustment(7.0), 0.1)

    def test_average_engagement(self):
        """2~5% → 0.0"""
        self.assertEqual(_engagement_adjustment(3.0), 0.0)

    def test_low_engagement(self):
        """1~2% → -0.1"""
        self.assertEqual(_engagement_adjustment(1.5), -0.1)

    def test_very_low_engagement(self):
        """1% 미만 → -0.2"""
        self.assertEqual(_engagement_adjustment(0.5), -0.2)


class TestGrowthAdjustment(unittest.TestCase):
    """성장률 조정 테스트"""

    def test_fast_growth(self):
        """5%+ → +0.2"""
        self.assertEqual(_growth_adjustment(10.0), 0.2)

    def test_moderate_growth(self):
        """1~5% → +0.1"""
        self.assertEqual(_growth_adjustment(3.0), 0.1)

    def test_stagnant(self):
        """-1~1% → 0.0"""
        self.assertEqual(_growth_adjustment(0.0), 0.0)

    def test_moderate_decline(self):
        """-5~-1% → -0.1"""
        self.assertEqual(_growth_adjustment(-3.0), -0.1)

    def test_sharp_decline(self):
        """-5% 미만 → -0.2"""
        self.assertEqual(_growth_adjustment(-10.0), -0.2)


class TestClamp(unittest.TestCase):
    """범위 제한 테스트"""

    def test_within_range(self):
        self.assertEqual(_clamp(5.0, 0.0, 10.0), 5.0)

    def test_below_min(self):
        self.assertEqual(_clamp(-1.0, 0.0, 10.0), 0.0)

    def test_above_max(self):
        self.assertEqual(_clamp(15.0, 0.0, 10.0), 10.0)


class TestDetermineAdjustment(unittest.TestCase):
    """조정 방향 결정 테스트"""

    def test_maintain(self):
        """차이 15% 미만 → maintain"""
        adj, reason = _determine_adjustment(3.0, 3.2)
        self.assertEqual(adj, "maintain")
        self.assertIn("유지", reason)

    def test_increase(self):
        """권장이 더 높으면 → increase"""
        adj, reason = _determine_adjustment(2.0, 4.0)
        self.assertEqual(adj, "increase")
        self.assertIn("늘리", reason)

    def test_decrease(self):
        """권장이 더 낮으면 → decrease"""
        adj, reason = _determine_adjustment(10.0, 5.0)
        self.assertEqual(adj, "decrease")
        self.assertIn("줄이", reason)


class TestCalculateVelocity(unittest.TestCase):
    """발행 속도 계산 통합 테스트"""

    def test_basic_calculation(self):
        """기본 계산"""
        result = calculate_velocity({"current_rate": 3.0})
        self.assertIsInstance(result, VelocityRecommendation)
        self.assertEqual(result.current_rate, 3.0)
        self.assertIn(result.adjustment, ("increase", "maintain", "decrease"))

    def test_large_channel_recommends_more(self):
        """대형 채널 → 더 높은 권장 속도"""
        small = calculate_velocity({"current_rate": 3.0, "subscribers": 100})
        large = calculate_velocity({"current_rate": 3.0, "subscribers": 200_000})
        self.assertGreaterEqual(large.recommended_rate, small.recommended_rate)

    def test_high_engagement_boosts(self):
        """높은 참여율 → 속도 증가 경향"""
        low_eng = calculate_velocity({
            "current_rate": 3.0, "engagement_rate": 0.5, "subscribers": 5000,
        })
        high_eng = calculate_velocity({
            "current_rate": 3.0, "engagement_rate": 15.0, "subscribers": 5000,
        })
        self.assertGreaterEqual(high_eng.recommended_rate, low_eng.recommended_rate)

    def test_negative_growth_slows(self):
        """급감하는 채널 → 속도 감소 경향"""
        growing = calculate_velocity({
            "current_rate": 5.0, "growth_rate": 10.0, "subscribers": 5000,
        })
        declining = calculate_velocity({
            "current_rate": 5.0, "growth_rate": -10.0, "subscribers": 5000,
        })
        self.assertGreaterEqual(growing.recommended_rate, declining.recommended_rate)

    def test_rate_within_bounds(self):
        """결과가 최소/최대 범위 내"""
        result = calculate_velocity({
            "current_rate": 100.0, "subscribers": 1_000_000,
            "engagement_rate": 50.0, "growth_rate": 50.0,
        })
        self.assertLessEqual(result.recommended_rate, 14.0)
        self.assertGreaterEqual(result.recommended_rate, 0.5)

    def test_default_values(self):
        """기본값 사용 (빈 dict)"""
        result = calculate_velocity({})
        self.assertEqual(result.current_rate, 3.0)  # 기본 rate
        self.assertIsNotNone(result.reason)

    def test_zero_current_rate_uses_default(self):
        """현재 속도 0 → 기본값 사용"""
        result = calculate_velocity({"current_rate": 0})
        self.assertEqual(result.current_rate, 0.0)
        self.assertGreater(result.recommended_rate, 0)

    def test_reason_is_korean(self):
        """이유가 한국어"""
        result = calculate_velocity({"current_rate": 3.0})
        # 한국어 포함 확인 (한글 유니코드 범위)
        has_korean = any('\uac00' <= c <= '\ud7a3' for c in result.reason)
        self.assertTrue(has_korean)


if __name__ == "__main__":
    unittest.main()
