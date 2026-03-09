"""시즌 예보 서비스 테스트"""
import unittest

from services.season_forecast_service import (
    SeasonForecast,
    PHASES,
    forecast_season,
    get_phase_label_kr,
    _normalize_topic,
    _keyword_match_scores,
    _hash_score,
)


class TestNormalizeTopic(unittest.TestCase):
    """주제 정규화 테스트"""

    def test_strip_whitespace(self):
        """앞뒤 공백 제거"""
        self.assertEqual(_normalize_topic("  AI 트렌드  "), "ai 트렌드")

    def test_collapse_spaces(self):
        """연속 공백 축소"""
        self.assertEqual(_normalize_topic("AI   트렌드"), "ai 트렌드")

    def test_lowercase(self):
        """소문자 변환"""
        self.assertEqual(_normalize_topic("PYTHON"), "python")


class TestHashScore(unittest.TestCase):
    """해시 점수 테스트"""

    def test_deterministic(self):
        """같은 입력은 항상 같은 결과"""
        s1 = _hash_score("AI")
        s2 = _hash_score("AI")
        self.assertEqual(s1, s2)

    def test_range(self):
        """0~1 범위"""
        for topic in ["python", "자바스크립트", "머신러닝", "블로그"]:
            score = _hash_score(topic)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_different_topics_different_scores(self):
        """다른 주제는 (대부분) 다른 점수"""
        s1 = _hash_score("python")
        s2 = _hash_score("javascript")
        self.assertNotEqual(s1, s2)


class TestKeywordMatchScores(unittest.TestCase):
    """키워드 매칭 점수 테스트"""

    def test_rising_keywords(self):
        """상승기 키워드 매칭"""
        scores = _keyword_match_scores("신규 출시 서비스")
        self.assertGreater(scores["rising"], 0)

    def test_peak_keywords(self):
        """정점기 키워드 매칭"""
        scores = _keyword_match_scores("인기 화제 콘텐츠")
        self.assertGreater(scores["peak"], 0)

    def test_no_match(self):
        """매칭 없는 경우 모두 0"""
        scores = _keyword_match_scores("단순한 주제")
        total = sum(scores.values())
        self.assertEqual(total, 0.0)

    def test_all_phases_present(self):
        """모든 단계 키가 존재"""
        scores = _keyword_match_scores("테스트")
        for phase in PHASES:
            self.assertIn(phase, scores)


class TestForecastSeason(unittest.TestCase):
    """시즌 예보 통합 테스트"""

    def test_empty_topic(self):
        """빈 주제 → 기본값 반환"""
        result = forecast_season("")
        self.assertIsInstance(result, SeasonForecast)
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("주제를 입력", result.recommendation)

    def test_whitespace_only(self):
        """공백만 입력 → 빈 주제 처리"""
        result = forecast_season("   ")
        self.assertEqual(result.confidence, 0.0)

    def test_rising_topic(self):
        """상승기 키워드 포함 주제"""
        result = forecast_season("신규 서비스 출시")
        self.assertEqual(result.phase, "rising")
        self.assertGreater(result.confidence, 0)
        self.assertIn("상승", result.recommendation)

    def test_peak_topic(self):
        """정점기 키워드 포함 주제"""
        result = forecast_season("인기 화제의 트렌드")
        self.assertEqual(result.phase, "peak")

    def test_declining_topic(self):
        """하락기 키워드 포함 주제"""
        result = forecast_season("하락하는 시장 감소")
        self.assertEqual(result.phase, "declining")

    def test_reignite_topic(self):
        """재점화기 키워드 포함 주제"""
        result = forecast_season("부활한 레트로 리메이크")
        self.assertEqual(result.phase, "reignite")

    def test_no_keyword_fallback(self):
        """키워드 없으면 해시 기반 폴백"""
        result = forecast_season("xyz123abc")
        self.assertIn(result.phase, PHASES)
        self.assertEqual(result.confidence, 0.3)

    def test_result_has_all_fields(self):
        """결과에 모든 필드가 있는지 확인"""
        result = forecast_season("테스트 주제")
        self.assertTrue(hasattr(result, "topic"))
        self.assertTrue(hasattr(result, "phase"))
        self.assertTrue(hasattr(result, "confidence"))
        self.assertTrue(hasattr(result, "recommendation"))

    def test_phase_is_valid(self):
        """반환된 단계가 유효한 값"""
        for topic in ["AI 런칭", "핫 트렌드", "쇠퇴 시장", "부활 브랜드", "xyz"]:
            result = forecast_season(topic)
            self.assertIn(result.phase, PHASES)


class TestGetPhaseLabelKr(unittest.TestCase):
    """단계 한국어 라벨 테스트"""

    def test_all_phases(self):
        """모든 단계에 한국어 라벨 존재"""
        expected = {
            "rising": "상승기",
            "peak": "정점기",
            "declining": "하락기",
            "reignite": "재점화기",
        }
        for phase, label in expected.items():
            self.assertEqual(get_phase_label_kr(phase), label)

    def test_unknown_phase(self):
        """알 수 없는 단계는 원문 반환"""
        self.assertEqual(get_phase_label_kr("unknown"), "unknown")


if __name__ == "__main__":
    unittest.main()
