"""게시 윈도우 예측 서비스 테스트"""
import unittest
from datetime import datetime

from services.post_window_service import (
    TimeSlot,
    predict_best_window,
    format_slot_kr,
    _parse_history,
    _aggregate_slots,
    _calculate_confidence,
    _default_slots,
)


class TestParseHistory(unittest.TestCase):
    """히스토리 파싱 테스트"""

    def test_parse_iso_string(self):
        """ISO 형식 문자열 파싱"""
        history = [{"posted_at": "2025-06-15T09:30:00", "engagement": 100}]
        result = _parse_history(history)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0].hour, 9)
        self.assertEqual(result[0][1], 100.0)

    def test_parse_datetime_object(self):
        """datetime 객체 직접 입력"""
        dt = datetime(2025, 6, 15, 14, 0)
        history = [{"posted_at": dt, "engagement": 50}]
        result = _parse_history(history)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0].hour, 14)

    def test_parse_invalid_date_skipped(self):
        """유효하지 않은 날짜는 건너뜀"""
        history = [
            {"posted_at": "not-a-date", "engagement": 10},
            {"posted_at": "2025-06-15T10:00:00", "engagement": 20},
        ]
        result = _parse_history(history)
        self.assertEqual(len(result), 1)

    def test_parse_missing_posted_at(self):
        """posted_at 누락 시 건너뜀"""
        history = [{"engagement": 10}]
        result = _parse_history(history)
        self.assertEqual(len(result), 0)

    def test_parse_missing_engagement_defaults_zero(self):
        """engagement 누락 시 0으로 처리"""
        history = [{"posted_at": "2025-06-15T10:00:00"}]
        result = _parse_history(history)
        self.assertEqual(result[0][1], 0.0)


class TestAggregateSlots(unittest.TestCase):
    """슬롯 집계 테스트"""

    def test_aggregate_same_slot(self):
        """같은 요일+시간은 하나의 슬롯으로 집계"""
        # 2025-06-16은 월요일
        parsed = [
            (datetime(2025, 6, 16, 9, 0), 100.0),
            (datetime(2025, 6, 23, 9, 0), 200.0),  # 다음 월요일
        ]
        slots = _aggregate_slots(parsed)
        self.assertIn(("Monday", 9), slots)
        self.assertEqual(len(slots[("Monday", 9)]), 2)

    def test_aggregate_different_slots(self):
        """다른 요일/시간은 별도 슬롯"""
        parsed = [
            (datetime(2025, 6, 16, 9, 0), 100.0),   # 월 9시
            (datetime(2025, 6, 17, 14, 0), 50.0),   # 화 14시
        ]
        slots = _aggregate_slots(parsed)
        self.assertEqual(len(slots), 2)


class TestCalculateConfidence(unittest.TestCase):
    """신뢰도 계산 테스트"""

    def test_zero_total(self):
        """전체 데이터 0건이면 신뢰도 0"""
        self.assertEqual(_calculate_confidence(0, 0), 0.0)

    def test_high_sample(self):
        """10건 이상이면 높은 신뢰도"""
        conf = _calculate_confidence(10, 10)
        self.assertGreaterEqual(conf, 0.5)

    def test_low_sample(self):
        """1건이면 낮은 신뢰도"""
        conf = _calculate_confidence(1, 100)
        self.assertLess(conf, 0.5)


class TestPredictBestWindow(unittest.TestCase):
    """최적 시간대 예측 통합 테스트"""

    def test_empty_history_returns_defaults(self):
        """빈 히스토리 → 기본 시간대 반환"""
        result = predict_best_window([])
        self.assertEqual(len(result), 5)
        self.assertIsInstance(result[0], TimeSlot)
        self.assertEqual(result[0].confidence, 0.0)

    def test_valid_history_returns_ranked_slots(self):
        """유효한 히스토리 → engagement 내림차순 정렬"""
        history = [
            {"posted_at": "2025-06-16T09:00:00", "engagement": 300},  # 월 9시
            {"posted_at": "2025-06-17T14:00:00", "engagement": 100},  # 화 14시
            {"posted_at": "2025-06-18T19:00:00", "engagement": 500},  # 수 19시
        ]
        result = predict_best_window(history, top_n=3)
        self.assertEqual(len(result), 3)
        # 가장 높은 engagement가 1등
        self.assertGreaterEqual(
            result[0].predicted_engagement,
            result[1].predicted_engagement,
        )

    def test_top_n_limits_results(self):
        """top_n 매개변수가 결과 수를 제한"""
        history = [
            {"posted_at": f"2025-06-{16+i}T{9+i}:00:00", "engagement": i * 10}
            for i in range(7)
        ]
        result = predict_best_window(history, top_n=2)
        self.assertLessEqual(len(result), 2)

    def test_followers_boost_primetime(self):
        """팔로워 1000+ 시 프라임타임 보너스 증가"""
        history = [
            {"posted_at": "2025-06-16T19:00:00", "engagement": 100},
        ]
        no_followers = predict_best_window(history, followers=0)
        with_followers = predict_best_window(history, followers=5000)
        # 19시는 프라임타임 → 팔로워 있을 때 더 높은 예측
        self.assertGreaterEqual(
            with_followers[0].predicted_engagement,
            no_followers[0].predicted_engagement,
        )

    def test_all_invalid_returns_defaults(self):
        """모든 레코드가 유효하지 않으면 기본값"""
        history = [
            {"posted_at": "bad-date", "engagement": 100},
            {"engagement": 200},
        ]
        result = predict_best_window(history)
        self.assertEqual(len(result), 5)
        self.assertEqual(result[0].confidence, 0.0)


class TestFormatSlotKr(unittest.TestCase):
    """한국어 포맷 테스트"""

    def test_format_monday(self):
        """월요일 포맷"""
        slot = TimeSlot("Monday", 9, 150.0, 0.8)
        formatted = format_slot_kr(slot)
        self.assertIn("월요일", formatted)
        self.assertIn("9시", formatted)

    def test_format_unknown_day(self):
        """알 수 없는 요일은 원문 유지"""
        slot = TimeSlot("Holiday", 12, 50.0, 0.5)
        formatted = format_slot_kr(slot)
        self.assertIn("Holiday", formatted)


class TestDefaultSlots(unittest.TestCase):
    """기본 시간대 테스트"""

    def test_default_slots_count(self):
        """기본 5개 슬롯 반환"""
        defaults = _default_slots()
        self.assertEqual(len(defaults), 5)

    def test_default_slots_zero_engagement(self):
        """기본 슬롯은 engagement/confidence 모두 0"""
        for slot in _default_slots():
            self.assertEqual(slot.predicted_engagement, 0.0)
            self.assertEqual(slot.confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
