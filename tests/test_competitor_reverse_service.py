"""
경쟁 역공학 서비스 단위 테스트
"""
import unittest
from services.competitor_reverse_service import (
    reverse_engineer,
    StrategyTemplate,
    _classify_posting_frequency,
    _extract_content_types,
    _extract_top_topics,
    _analyze_engagement_patterns,
)


class TestCompetitorReverseService(unittest.TestCase):
    """reverse_engineer 함수 단위 테스트"""

    def test_basic_reverse_engineer(self):
        """기본 역공학 — 유효한 채널 데이터"""
        channel = {
            "name": "테크채널",
            "posts": [
                {"text": "Python 튜토리얼 방법 가이드", "engagement": 5000},
                {"text": "AI 뉴스 소식 발표", "engagement": 8000},
                {"text": "React 리뷰 비교 후기", "engagement": 3000},
            ],
        }
        result = reverse_engineer(channel)
        self.assertIsInstance(result, StrategyTemplate)
        self.assertEqual(result.competitor, "테크채널")
        self.assertTrue(len(result.content_types) > 0)
        self.assertTrue(len(result.recommendations) > 0)

    def test_empty_posts(self):
        """빈 포스트 목록 — 안전하게 처리"""
        channel = {"name": "빈채널", "posts": []}
        result = reverse_engineer(channel)
        self.assertEqual(result.competitor, "빈채널")
        self.assertEqual(result.posting_frequency, "unknown")
        self.assertEqual(result.content_types, [])
        self.assertIn("데이터 부족", result.engagement_patterns)

    def test_no_name(self):
        """채널명 없으면 Unknown"""
        result = reverse_engineer({"posts": [{"text": "test", "engagement": 1}]})
        self.assertEqual(result.competitor, "Unknown")

    def test_timestamp_based_frequency(self):
        """타임스탬프 기반 포스팅 빈도 계산"""
        # 하루 간격 = daily
        channel = {
            "name": "일간채널",
            "posts": [
                {"text": "글1", "engagement": 100, "timestamp": 1000000},
                {"text": "글2", "engagement": 200, "timestamp": 1086400},
                {"text": "글3", "engagement": 150, "timestamp": 1172800},
            ],
        }
        result = reverse_engineer(channel)
        self.assertEqual(result.posting_frequency, "daily")

    def test_classify_posting_frequency(self):
        """빈도 분류 함수 직접 테스트"""
        self.assertEqual(_classify_posting_frequency(1.0), "daily")
        self.assertEqual(_classify_posting_frequency(3.0), "weekly")
        self.assertEqual(_classify_posting_frequency(8.0), "biweekly")
        self.assertEqual(_classify_posting_frequency(30.0), "monthly")
        self.assertEqual(_classify_posting_frequency(60.0), "irregular")

    def test_extract_content_types(self):
        """콘텐츠 유형 추출"""
        posts = [
            {"text": "Python 하는 법 tutorial"},
            {"text": "최신 리뷰 비교"},
        ]
        types = _extract_content_types(posts)
        self.assertIn("tutorial", types)
        self.assertIn("review", types)

    def test_extract_content_types_general(self):
        """유형 매칭 안 되면 general"""
        posts = [{"text": "일반적인 텍스트입니다"}]
        types = _extract_content_types(posts)
        self.assertEqual(types, ["general"])

    def test_extract_top_topics(self):
        """토픽 추출 — 빈도 기반"""
        posts = [
            {"text": "Python AI 머신러닝"},
            {"text": "Python 데이터 분석 AI"},
            {"text": "Python 개발 AI 모델"},
        ]
        topics = _extract_top_topics(posts, top_n=3)
        # python, ai가 가장 빈번
        self.assertIn("python", topics)
        self.assertTrue(len(topics) <= 3)

    def test_engagement_patterns_high(self):
        """높은 인게이지먼트 패턴"""
        posts = [
            {"text": "글1", "engagement": 15000},
            {"text": "글2", "engagement": 20000},
        ]
        patterns = _analyze_engagement_patterns(posts)
        self.assertTrue(any("높은" in p for p in patterns))

    def test_engagement_patterns_volatile(self):
        """변동성 높은 인게이지먼트"""
        posts = [
            {"text": "글1", "engagement": 100},
            {"text": "글2", "engagement": 50000},
        ]
        patterns = _analyze_engagement_patterns(posts)
        self.assertTrue(any("변동성" in p for p in patterns))

    def test_recommendations_generated(self):
        """추천 항목이 생성되는지 확인"""
        channel = {
            "name": "테스트채널",
            "posts": [
                {"text": "Python 튜토리얼 방법", "engagement": 500},
            ],
        }
        result = reverse_engineer(channel)
        self.assertTrue(len(result.recommendations) >= 1)

    def test_many_posts_no_error(self):
        """다수 포스트 처리 시 에러 없음"""
        posts = [{"text": f"콘텐츠 {i} 테스트 글", "engagement": i * 10} for i in range(100)]
        channel = {"name": "대량채널", "posts": posts}
        result = reverse_engineer(channel)
        self.assertIsInstance(result, StrategyTemplate)
        self.assertTrue(len(result.top_topics) > 0)


if __name__ == '__main__':
    unittest.main()
