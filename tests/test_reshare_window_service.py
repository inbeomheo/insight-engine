"""reshare_window_service 단위 테스트"""
import unittest
from datetime import datetime, timedelta

from services.reshare_window_service import (
    find_reshare_windows,
    ReshareWindow,
    _is_evergreen,
    _calculate_performance_score,
    _parse_date,
    _days_since_publish,
    _find_next_interval,
)


class TestParseDate(unittest.TestCase):

    def test_iso_format(self):
        result = _parse_date('2025-06-15')
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)

    def test_iso_with_time(self):
        result = _parse_date('2025-06-15T10:30:00')
        self.assertEqual(result.year, 2025)

    def test_slash_format(self):
        result = _parse_date('2025/06/15')
        self.assertIsNotNone(result)

    def test_dot_format(self):
        result = _parse_date('2025.06.15')
        self.assertIsNotNone(result)

    def test_invalid_returns_none(self):
        self.assertIsNone(_parse_date('invalid'))
        self.assertIsNone(_parse_date(''))


class TestIsEvergreen(unittest.TestCase):

    def test_guide_is_evergreen(self):
        self.assertTrue(_is_evergreen({'title': 'Python 가이드'}))

    def test_tutorial_is_evergreen(self):
        self.assertTrue(_is_evergreen({'title': 'tutorial for beginners'}))

    def test_tags_check(self):
        self.assertTrue(_is_evergreen({'title': '기사', 'tags': ['팁', '모음']}))

    def test_not_evergreen(self):
        self.assertFalse(_is_evergreen({'title': '오늘의 뉴스'}))


class TestCalculatePerformanceScore(unittest.TestCase):

    def test_high_engagement(self):
        score = _calculate_performance_score({'engagement': 0.9, 'views': 10000, 'shares': 100})
        self.assertGreater(score, 0.5)

    def test_zero_stats(self):
        score = _calculate_performance_score({})
        self.assertEqual(score, 0.0)

    def test_views_normalized(self):
        score = _calculate_performance_score({'views': 20000})
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)


class TestDaysSincePublish(unittest.TestCase):

    def test_recent_publish(self):
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        days = _days_since_publish({'published_date': yesterday}, datetime.now())
        self.assertIn(days, [0, 1, 2])  # 시간대 차이 허용

    def test_missing_date(self):
        self.assertIsNone(_days_since_publish({}, datetime.now()))

    def test_date_key_fallback(self):
        old = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        days = _days_since_publish({'date': old}, datetime.now())
        self.assertGreaterEqual(days, 29)


class TestFindNextInterval(unittest.TestCase):

    def test_recent_content(self):
        interval = _find_next_interval(5)
        self.assertIsNotNone(interval)
        self.assertEqual(interval['days'], 7)

    def test_month_old(self):
        interval = _find_next_interval(10)
        self.assertIsNotNone(interval)
        self.assertEqual(interval['days'], 30)

    def test_very_old(self):
        interval = _find_next_interval(400)
        self.assertIsNone(interval)


class TestFindReshareWindows(unittest.TestCase):

    def test_empty_history(self):
        result = find_reshare_windows([])
        self.assertEqual(result, [])

    def test_recent_content_skipped(self):
        """3일 이내 콘텐츠는 재공유 불필요"""
        today = datetime.now().strftime('%Y-%m-%d')
        history = [{'id': 'c1', 'published_date': today}]
        result = find_reshare_windows(history)
        self.assertEqual(len(result), 0)

    def test_week_old_content(self):
        week_ago = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        history = [{'id': 'c1', 'published_date': week_ago, 'title': 'test'}]
        result = find_reshare_windows(history)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], ReshareWindow)
        self.assertEqual(result[0].content_id, 'c1')

    def test_sorted_by_boost_desc(self):
        base = datetime.now()
        history = [
            {'id': 'old', 'published_date': (base - timedelta(days=100)).strftime('%Y-%m-%d'),
             'engagement': 0.3},
            {'id': 'recent', 'published_date': (base - timedelta(days=5)).strftime('%Y-%m-%d'),
             'engagement': 0.9},
        ]
        result = find_reshare_windows(history)
        if len(result) >= 2:
            boosts = [w.expected_boost for w in result]
            self.assertEqual(boosts, sorted(boosts, reverse=True))

    def test_evergreen_boost(self):
        """에버그린 콘텐츠는 부스트 상향"""
        week_ago = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        normal = [{'id': 'n', 'published_date': week_ago, 'title': '일반 글', 'engagement': 0.5}]
        evergreen = [{'id': 'e', 'published_date': week_ago, 'title': '완벽 가이드', 'engagement': 0.5}]
        normal_result = find_reshare_windows(normal)
        evergreen_result = find_reshare_windows(evergreen)
        self.assertGreater(
            evergreen_result[0].expected_boost,
            normal_result[0].expected_boost,
        )

    def test_optimal_date_format(self):
        old = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        history = [{'id': 'x', 'published_date': old}]
        result = find_reshare_windows(history)
        self.assertTrue(len(result) > 0)
        # YYYY-MM-DD 형식 확인
        try:
            datetime.strptime(result[0].optimal_date, '%Y-%m-%d')
        except ValueError:
            self.fail("optimal_date가 YYYY-MM-DD 형식이 아닙니다")

    def test_reason_not_empty(self):
        old = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        history = [{'id': 'x', 'published_date': old}]
        result = find_reshare_windows(history)
        self.assertTrue(len(result[0].reason) > 0)

    def test_content_id_fallback(self):
        old = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        history = [{'content_id': 'alt_id', 'published_date': old}]
        result = find_reshare_windows(history)
        self.assertEqual(result[0].content_id, 'alt_id')

    def test_missing_id_skipped(self):
        old = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        history = [{'published_date': old}]
        result = find_reshare_windows(history)
        self.assertEqual(len(result), 0)


if __name__ == '__main__':
    unittest.main()
