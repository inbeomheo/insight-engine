"""
감성 타임라인 서비스 단위 테스트
"""
import unittest
from services.sentiment_timeline_service import (
    build_sentiment_timeline,
    SentimentTimeline,
    SentimentPoint,
    _compute_sentiment,
    _determine_trend,
    _make_excerpt,
)


class TestSentimentTimelineService(unittest.TestCase):
    """build_sentiment_timeline 함수 단위 테스트"""

    def test_basic_timeline(self):
        """기본 타임라인 생성"""
        texts = [
            {"text": "정말 좋은 영상입니다 훌륭해요", "timestamp": "2026-01-01"},
            {"text": "별로 실망했어요", "timestamp": "2026-01-02"},
            {"text": "유익한 내용이네요 감사합니다", "timestamp": "2026-01-03"},
        ]
        result = build_sentiment_timeline("content_1", texts)
        self.assertIsInstance(result, SentimentTimeline)
        self.assertEqual(result.content_id, "content_1")
        self.assertEqual(len(result.points), 3)
        self.assertIn(result.trend, ["improving", "declining", "stable"])

    def test_empty_texts(self):
        """빈 텍스트 리스트"""
        result = build_sentiment_timeline("empty", [])
        self.assertEqual(result.content_id, "empty")
        self.assertEqual(result.points, [])
        self.assertEqual(result.trend, "stable")
        self.assertEqual(result.average_sentiment, 0.0)

    def test_positive_sentiment(self):
        """긍정 텍스트 감성 점수"""
        score, label = _compute_sentiment("정말 좋은 영상 훌륭합니다 최고예요")
        self.assertGreater(score, 0)
        self.assertEqual(label, "positive")

    def test_negative_sentiment(self):
        """부정 텍스트 감성 점수"""
        score, label = _compute_sentiment("별로 실망 최악이에요 문제가 많아요")
        self.assertLess(score, 0)
        self.assertEqual(label, "negative")

    def test_neutral_sentiment(self):
        """중립 텍스트 감성 점수"""
        score, label = _compute_sentiment("오늘 날씨가 맑습니다")
        self.assertEqual(score, 0.0)
        self.assertEqual(label, "neutral")

    def test_english_sentiment(self):
        """영어 감성 분석"""
        score, label = _compute_sentiment("This is great and amazing content!")
        self.assertGreater(score, 0)
        self.assertEqual(label, "positive")

    def test_trend_improving(self):
        """개선 추세 감지"""
        points = [
            SentimentPoint("t1", -0.5, "negative", "나쁨"),
            SentimentPoint("t2", -0.3, "negative", "조금 나쁨"),
            SentimentPoint("t3", 0.3, "positive", "좋음"),
            SentimentPoint("t4", 0.8, "positive", "매우 좋음"),
        ]
        trend = _determine_trend(points)
        self.assertEqual(trend, "improving")

    def test_trend_declining(self):
        """하락 추세 감지"""
        points = [
            SentimentPoint("t1", 0.8, "positive", "좋음"),
            SentimentPoint("t2", 0.5, "positive", "보통"),
            SentimentPoint("t3", -0.3, "negative", "나쁨"),
            SentimentPoint("t4", -0.7, "negative", "매우 나쁨"),
        ]
        trend = _determine_trend(points)
        self.assertEqual(trend, "declining")

    def test_trend_stable(self):
        """안정 추세"""
        points = [
            SentimentPoint("t1", 0.3, "positive", "a"),
            SentimentPoint("t2", 0.35, "positive", "b"),
        ]
        trend = _determine_trend(points)
        self.assertEqual(trend, "stable")

    def test_make_excerpt_short(self):
        """짧은 텍스트 발췌 — 그대로 반환"""
        self.assertEqual(_make_excerpt("짧은 글"), "짧은 글")

    def test_make_excerpt_long(self):
        """긴 텍스트 발췌 — 잘림"""
        long_text = "가" * 100
        excerpt = _make_excerpt(long_text, max_len=50)
        self.assertTrue(excerpt.endswith("..."))
        self.assertEqual(len(excerpt), 53)  # 50 + "..."

    def test_average_sentiment(self):
        """평균 감성 점수 계산"""
        texts = [
            {"text": "좋아요 훌륭해요", "timestamp": "2026-01-01"},
            {"text": "좋아요 최고", "timestamp": "2026-01-02"},
        ]
        result = build_sentiment_timeline("avg_test", texts)
        self.assertGreater(result.average_sentiment, 0)

    def test_timestamps_sorted(self):
        """타임스탬프 순 정렬"""
        texts = [
            {"text": "나중 글", "timestamp": "2026-01-03"},
            {"text": "처음 글", "timestamp": "2026-01-01"},
            {"text": "중간 글", "timestamp": "2026-01-02"},
        ]
        result = build_sentiment_timeline("sort_test", texts)
        ts_list = [p.timestamp for p in result.points]
        self.assertEqual(ts_list, sorted(ts_list))

    def test_blank_text_skipped(self):
        """공백 텍스트는 건너뜀"""
        texts = [
            {"text": "   ", "timestamp": "2026-01-01"},
            {"text": "좋은 내용", "timestamp": "2026-01-02"},
        ]
        result = build_sentiment_timeline("blank_test", texts)
        self.assertEqual(len(result.points), 1)


if __name__ == '__main__':
    unittest.main()
