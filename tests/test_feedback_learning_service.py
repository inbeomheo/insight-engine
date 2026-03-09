"""피드백 학습 서비스 테스트."""

import unittest
from services.feedback_learning_service import (
    Feedback,
    LearningInsight,
    record_feedback,
    analyze_feedback,
    get_improvement_suggestions,
    calculate_satisfaction_trend,
)


class TestRecordFeedback(unittest.TestCase):
    """피드백 기록 테스트."""

    def test_record_basic(self):
        """기본 피드백 기록."""
        fb = record_feedback("c1", 4, "좋은 품질", "quality")
        self.assertEqual(fb.content_id, "c1")
        self.assertEqual(fb.rating, 4)
        self.assertEqual(fb.comment, "좋은 품질")
        self.assertEqual(fb.category, "quality")
        self.assertTrue(fb.feedback_id)
        self.assertTrue(fb.timestamp)

    def test_record_invalid_rating_low(self):
        """범위 미만 평점 → ValueError."""
        with self.assertRaises(ValueError):
            record_feedback("c1", 0, "코멘트", "quality")

    def test_record_invalid_rating_high(self):
        """범위 초과 평점 → ValueError."""
        with self.assertRaises(ValueError):
            record_feedback("c1", 6, "코멘트", "quality")

    def test_record_invalid_category(self):
        """잘못된 카테고리 → ValueError."""
        with self.assertRaises(ValueError):
            record_feedback("c1", 3, "코멘트", "invalid_category")

    def test_record_all_valid_categories(self):
        """모든 유효 카테고리 테스트."""
        for cat in ["quality", "style", "accuracy", "relevance"]:
            fb = record_feedback("c1", 3, "테스트", cat)
            self.assertEqual(fb.category, cat)

    def test_record_boundary_ratings(self):
        """경계값 평점 (1, 5)."""
        fb1 = record_feedback("c1", 1, "최저", "quality")
        fb5 = record_feedback("c2", 5, "최고", "quality")
        self.assertEqual(fb1.rating, 1)
        self.assertEqual(fb5.rating, 5)


class TestAnalyzeFeedback(unittest.TestCase):
    """피드백 분석 테스트."""

    def _make_feedback(self, content_id, rating, comment, category):
        return record_feedback(content_id, rating, comment, category)

    def test_analyze_empty(self):
        """빈 피드백 목록 → 빈 인사이트."""
        result = analyze_feedback([])
        self.assertEqual(result, [])

    def test_analyze_keyword_frequency(self):
        """키워드 빈도 3회 이상 패턴 추출."""
        feedbacks = [
            self._make_feedback("c1", 2, "품질이 낮다", "quality"),
            self._make_feedback("c2", 1, "품질이 문제", "quality"),
            self._make_feedback("c3", 2, "품질이 부족", "quality"),
        ]
        insights = analyze_feedback(feedbacks)
        # "품질이"가 3회 반복 → 패턴으로 추출
        patterns = [i.pattern for i in insights]
        self.assertTrue(any("품질이" in p for p in patterns))

    def test_analyze_category_pattern(self):
        """카테고리별 반복 패턴 (3회 이상)."""
        feedbacks = [
            self._make_feedback("c1", 4, "좋다", "style"),
            self._make_feedback("c2", 5, "훌륭", "style"),
            self._make_feedback("c3", 4, "만족", "style"),
        ]
        insights = analyze_feedback(feedbacks)
        patterns = [i.pattern for i in insights]
        self.assertIn("category:style", patterns)

    def test_analyze_low_rating_suggestion(self):
        """낮은 평점 패턴 → 개선 필요 제안."""
        feedbacks = [
            self._make_feedback("c1", 1, "정확도 부족 문제", "accuracy"),
            self._make_feedback("c2", 2, "정확도 부족 원인", "accuracy"),
            self._make_feedback("c3", 1, "정확도 부족 개선", "accuracy"),
        ]
        insights = analyze_feedback(feedbacks)
        # "정확도" 3회 → 낮은 평점 → 개선 필요
        accuracy_insights = [i for i in insights if "정확도" in i.pattern]
        if accuracy_insights:
            self.assertIn("개선 필요", accuracy_insights[0].suggestion)

    def test_analyze_high_rating_suggestion(self):
        """높은 평점 패턴 → 유지 제안."""
        feedbacks = [
            self._make_feedback("c1", 5, "구성이 좋다", "quality"),
            self._make_feedback("c2", 4, "구성이 훌륭", "quality"),
            self._make_feedback("c3", 5, "구성이 최고", "quality"),
        ]
        insights = analyze_feedback(feedbacks)
        # "구성이" 3회 → 높은 평점 → 유지
        good_insights = [i for i in insights if "구성이" in i.pattern]
        if good_insights:
            self.assertIn("유지", good_insights[0].suggestion)

    def test_analyze_frequency_sorted(self):
        """인사이트가 빈도 내림차순 정렬."""
        feedbacks = [
            self._make_feedback(f"c{i}", 3, "반복 키워드 포함", "quality")
            for i in range(5)
        ]
        insights = analyze_feedback(feedbacks)
        if len(insights) >= 2:
            for i in range(len(insights) - 1):
                self.assertGreaterEqual(insights[i].frequency, insights[i + 1].frequency)

    def test_analyze_below_threshold_excluded(self):
        """빈도 3회 미만 키워드는 제외."""
        feedbacks = [
            self._make_feedback("c1", 3, "고유한_단어A", "quality"),
            self._make_feedback("c2", 3, "고유한_단어B", "quality"),
        ]
        insights = analyze_feedback(feedbacks)
        keyword_insights = [i for i in insights if not i.pattern.startswith("category:")]
        # 2회만 등장한 키워드는 추출 안 됨
        self.assertEqual(len(keyword_insights), 0)


class TestGetImprovementSuggestions(unittest.TestCase):
    """개선 제안 테스트."""

    def test_suggestions_empty(self):
        """빈 인사이트 → 빈 제안."""
        self.assertEqual(get_improvement_suggestions([]), [])

    def test_suggestions_low_rating_first(self):
        """낮은 평점 인사이트가 먼저 제안됨."""
        insights = [
            LearningInsight("i1", "좋은패턴", 5, 4.5, "유지하세요"),
            LearningInsight("i2", "나쁜패턴", 3, 1.5, "개선 필요"),
        ]
        suggestions = get_improvement_suggestions(insights)
        self.assertEqual(suggestions[0], "개선 필요")

    def test_suggestions_count(self):
        """인사이트 수만큼 제안 생성."""
        insights = [
            LearningInsight(f"i{i}", f"패턴{i}", 3, float(i), f"제안{i}")
            for i in range(1, 4)
        ]
        suggestions = get_improvement_suggestions(insights)
        self.assertEqual(len(suggestions), 3)


class TestCalculateSatisfactionTrend(unittest.TestCase):
    """만족도 추이 테스트."""

    def test_trend_empty(self):
        """빈 피드백 → 기본값."""
        result = calculate_satisfaction_trend([])
        self.assertEqual(result["average"], 0.0)
        self.assertEqual(result["trend"], "stable")
        self.assertEqual(result["count"], 0)

    def test_trend_average(self):
        """평균 계산."""
        feedbacks = [
            record_feedback("c1", 4, "좋음", "quality"),
            record_feedback("c2", 2, "나쁨", "quality"),
        ]
        result = calculate_satisfaction_trend(feedbacks)
        self.assertEqual(result["average"], 3.0)
        self.assertEqual(result["count"], 2)

    def test_trend_improving(self):
        """전반부 < 후반부 → improving."""
        feedbacks = [
            record_feedback(f"c{i}", 2, "초기", "quality")
            for i in range(4)
        ] + [
            record_feedback(f"c{i+4}", 5, "개선", "quality")
            for i in range(4)
        ]
        result = calculate_satisfaction_trend(feedbacks)
        self.assertEqual(result["trend"], "improving")

    def test_trend_declining(self):
        """전반부 > 후반부 → declining."""
        feedbacks = [
            record_feedback(f"c{i}", 5, "좋았음", "quality")
            for i in range(4)
        ] + [
            record_feedback(f"c{i+4}", 1, "나빠짐", "quality")
            for i in range(4)
        ]
        result = calculate_satisfaction_trend(feedbacks)
        self.assertEqual(result["trend"], "declining")

    def test_trend_stable(self):
        """변동 적으면 stable."""
        feedbacks = [
            record_feedback(f"c{i}", 3, "보통", "quality")
            for i in range(6)
        ]
        result = calculate_satisfaction_trend(feedbacks)
        self.assertEqual(result["trend"], "stable")

    def test_trend_distribution(self):
        """평점 분포."""
        feedbacks = [
            record_feedback("c1", 5, "최고", "quality"),
            record_feedback("c2", 5, "최고", "quality"),
            record_feedback("c3", 3, "보통", "quality"),
        ]
        result = calculate_satisfaction_trend(feedbacks)
        self.assertEqual(result["rating_distribution"][5], 2)
        self.assertEqual(result["rating_distribution"][3], 1)


if __name__ == "__main__":
    unittest.main()
