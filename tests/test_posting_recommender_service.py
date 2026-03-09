"""posting_recommender_service 단위 테스트"""
import unittest

from services.posting_recommender_service import (
    recommend_posting,
    PostingSlot,
    _normalize_day,
    _extract_engagement,
    _build_slot_stats,
    _generate_default_slots,
)


class TestNormalizeDay(unittest.TestCase):
    """요일 정규화 테스트"""

    def test_full_name_lowercase(self):
        self.assertEqual(_normalize_day('monday'), 'Monday')
        self.assertEqual(_normalize_day('friday'), 'Friday')

    def test_abbreviated(self):
        self.assertEqual(_normalize_day('mon'), 'Monday')
        self.assertEqual(_normalize_day('thu'), 'Thursday')

    def test_case_insensitive(self):
        self.assertEqual(_normalize_day('TUESDAY'), 'Tuesday')
        self.assertEqual(_normalize_day('Wed'), 'Wednesday')

    def test_invalid_day(self):
        self.assertIsNone(_normalize_day('notaday'))
        self.assertIsNone(_normalize_day(''))

    def test_whitespace_handling(self):
        self.assertEqual(_normalize_day('  sunday  '), 'Sunday')


class TestExtractEngagement(unittest.TestCase):
    """참여도 추출 테스트"""

    def test_direct_engagement(self):
        self.assertAlmostEqual(_extract_engagement({'engagement': 0.85}), 0.85)

    def test_likes_comments_ratio(self):
        entry = {'likes': 50, 'comments': 10, 'views': 1000}
        result = _extract_engagement(entry)
        expected = (50 * 0.4 + 10 * 0.6) / 1000
        self.assertAlmostEqual(result, expected)

    def test_capped_at_one(self):
        entry = {'likes': 9999, 'comments': 9999, 'views': 1}
        result = _extract_engagement(entry)
        self.assertLessEqual(result, 1.0)

    def test_zero_views(self):
        entry = {'likes': 10, 'comments': 5}
        result = _extract_engagement(entry)
        # views 0이면 score 그대로 (cap 적용)
        self.assertGreaterEqual(result, 0.0)


class TestBuildSlotStats(unittest.TestCase):
    """슬롯 통계 구축 테스트"""

    def test_valid_history(self):
        history = [
            {'day': 'monday', 'hour': 9, 'engagement': 0.5},
            {'day': 'monday', 'hour': 9, 'engagement': 0.7},
            {'day': 'tuesday', 'hour': 20, 'engagement': 0.9},
        ]
        stats = _build_slot_stats(history)
        self.assertEqual(len(stats[('Monday', 9)]), 2)
        self.assertEqual(len(stats[('Tuesday', 20)]), 1)

    def test_invalid_entries_skipped(self):
        history = [
            {'day': 'invalid', 'hour': 9, 'engagement': 0.5},
            {'hour': 9, 'engagement': 0.5},  # day 없음
            {'day': 'monday', 'engagement': 0.5},  # hour 없음
        ]
        stats = _build_slot_stats(history)
        self.assertEqual(len(stats), 0)

    def test_hour_range_validation(self):
        history = [
            {'day': 'monday', 'hour': -1, 'engagement': 0.5},
            {'day': 'monday', 'hour': 24, 'engagement': 0.5},
            {'day': 'monday', 'hour': 12, 'engagement': 0.5},
        ]
        stats = _build_slot_stats(history)
        self.assertEqual(len(stats), 1)
        self.assertIn(('Monday', 12), stats)


class TestRecommendPosting(unittest.TestCase):
    """포스팅 추천 메인 함수 테스트"""

    def test_empty_history_returns_defaults(self):
        result = recommend_posting([])
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)
        self.assertIsInstance(result[0], PostingSlot)

    def test_returns_posting_slots(self):
        history = [
            {'day': 'monday', 'hour': 9, 'engagement': 0.8},
            {'day': 'monday', 'hour': 9, 'engagement': 0.9},
            {'day': 'friday', 'hour': 18, 'engagement': 0.6},
        ]
        result = recommend_posting(history)
        self.assertIsInstance(result, list)
        for slot in result:
            self.assertIsInstance(slot, PostingSlot)
            self.assertIn(slot.day_of_week, [
                'Monday', 'Tuesday', 'Wednesday', 'Thursday',
                'Friday', 'Saturday', 'Sunday',
            ])
            self.assertTrue(0 <= slot.hour <= 23)
            self.assertTrue(0 <= slot.estimated_engagement <= 1.0)

    def test_top_n_limit(self):
        history = [
            {'day': 'monday', 'hour': i, 'engagement': 0.5}
            for i in range(10)
        ]
        result = recommend_posting(history, top_n=3)
        self.assertEqual(len(result), 3)

    def test_sorted_by_engagement_desc(self):
        history = [
            {'day': 'monday', 'hour': 9, 'engagement': 0.3},
            {'day': 'tuesday', 'hour': 20, 'engagement': 0.9},
            {'day': 'wednesday', 'hour': 12, 'engagement': 0.6},
        ]
        result = recommend_posting(history)
        engagements = [s.estimated_engagement for s in result]
        self.assertEqual(engagements, sorted(engagements, reverse=True))

    def test_reason_contains_day_and_hour(self):
        history = [
            {'day': 'thursday', 'hour': 15, 'engagement': 0.7},
        ]
        result = recommend_posting(history)
        self.assertTrue(len(result) > 0)
        self.assertIn('Thursday', result[0].reason)
        self.assertIn('15', result[0].reason)

    def test_day_of_week_key_support(self):
        """day_of_week 키도 지원하는지 확인"""
        history = [
            {'day_of_week': 'saturday', 'hour': 10, 'engagement': 0.75},
        ]
        result = recommend_posting(history)
        self.assertTrue(any(s.day_of_week == 'Saturday' for s in result))

    def test_confidence_bonus_with_more_data(self):
        """데이터가 많으면 신뢰도 보너스 적용"""
        history_small = [
            {'day': 'monday', 'hour': 9, 'engagement': 0.5},
        ]
        history_large = [
            {'day': 'monday', 'hour': 9, 'engagement': 0.5}
            for _ in range(15)
        ]
        result_small = recommend_posting(history_small)
        result_large = recommend_posting(history_large)
        # 같은 평균이어도 데이터가 많으면 점수가 높아야 함
        small_eng = next(s.estimated_engagement for s in result_small if s.day_of_week == 'Monday')
        large_eng = next(s.estimated_engagement for s in result_large if s.day_of_week == 'Monday')
        self.assertGreaterEqual(large_eng, small_eng)


class TestGenerateDefaultSlots(unittest.TestCase):
    """기본 추천 슬롯 테스트"""

    def test_returns_requested_count(self):
        result = _generate_default_slots(3)
        self.assertEqual(len(result), 3)

    def test_default_slots_are_posting_slots(self):
        result = _generate_default_slots(5)
        for slot in result:
            self.assertIsInstance(slot, PostingSlot)
            self.assertIsInstance(slot.reason, str)
            self.assertTrue(len(slot.reason) > 0)


if __name__ == '__main__':
    unittest.main()
