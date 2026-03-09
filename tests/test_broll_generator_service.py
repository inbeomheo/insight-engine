"""
BrollGeneratorService 단위 테스트 (T12.3)
"""
import unittest
from services.broll_generator_service import (
    generate_broll,
    BrollSuggestion,
    _extract_keywords,
    _infer_visual_type,
    _calculate_relevance,
    _estimate_duration,
    _build_description,
    VISUAL_TYPES,
)


class TestExtractKeywords(unittest.TestCase):
    """키워드 추출 테스트"""

    def test_basic_extraction(self):
        keywords = _extract_keywords("demo tutorial setup")
        self.assertIn("demo", keywords)
        self.assertIn("tutorial", keywords)

    def test_empty_text(self):
        self.assertEqual(_extract_keywords(''), [])

    def test_short_words_excluded(self):
        """2글자 미만 단어 제외"""
        keywords = _extract_keywords("a b cd ef")
        self.assertNotIn("a", keywords)
        self.assertNotIn("b", keywords)
        self.assertIn("cd", keywords)

    def test_duplicates_removed(self):
        """중복 키워드 제거"""
        keywords = _extract_keywords("demo demo demo")
        self.assertEqual(keywords.count("demo"), 1)

    def test_korean_keywords(self):
        """한국어 키워드 추출"""
        keywords = _extract_keywords("설치 방법 튜토리얼 가이드")
        self.assertIn("설치", keywords)
        self.assertIn("튜토리얼", keywords)


class TestInferVisualType(unittest.TestCase):
    """시각 자료 유형 추론 테스트"""

    def test_screen_recording(self):
        self.assertEqual(_infer_visual_type(["demo", "setup"]), "screen_recording")

    def test_infographic(self):
        self.assertEqual(_infer_visual_type(["data", "statistics"]), "infographic")

    def test_animation(self):
        self.assertEqual(_infer_visual_type(["process", "workflow"]), "animation")

    def test_photo(self):
        self.assertEqual(_infer_visual_type(["portrait", "product"]), "photo")

    def test_default_stock_video(self):
        """매핑되지 않는 키워드 → stock_video"""
        self.assertEqual(_infer_visual_type(["unknown", "keyword"]), "stock_video")

    def test_korean_keyword_mapping(self):
        """한국어 키워드 매핑"""
        self.assertEqual(_infer_visual_type(["설치"]), "screen_recording")
        self.assertEqual(_infer_visual_type(["통계"]), "infographic")


class TestCalculateRelevance(unittest.TestCase):
    """관련도 점수 계산 테스트"""

    def test_base_score(self):
        """기본 점수는 0.5"""
        score = _calculate_relevance("text", "", [])
        self.assertEqual(score, 0.5)

    def test_many_keywords_bonus(self):
        """키워드 5개 이상 → 추가 점수"""
        keywords = ["a", "b", "c", "d", "e"]
        score = _calculate_relevance("text", "", keywords)
        self.assertGreater(score, 0.5)

    def test_context_matching_bonus(self):
        """컨텍스트에 키워드가 포함되면 추가 점수"""
        score = _calculate_relevance("demo tutorial", "demo video tutorial", ["demo", "tutorial"])
        self.assertGreater(score, 0.5)

    def test_max_score_capped(self):
        """최대 점수는 1.0"""
        keywords = ["a", "b", "c", "d", "e", "f", "g", "h"]
        score = _calculate_relevance("text", "a b c d e f g h", keywords)
        self.assertLessEqual(score, 1.0)


class TestEstimateDuration(unittest.TestCase):
    """B-roll 길이 추정 테스트"""

    def test_short_gap(self):
        self.assertEqual(_estimate_duration("짧은 문장"), 3)

    def test_medium_gap(self):
        text = " ".join(["단어"] * 10)
        self.assertEqual(_estimate_duration(text), 5)

    def test_long_gap(self):
        text = " ".join(["단어"] * 25)
        self.assertEqual(_estimate_duration(text), 8)

    def test_very_long_gap(self):
        text = " ".join(["단어"] * 50)
        self.assertEqual(_estimate_duration(text), 10)


class TestBuildDescription(unittest.TestCase):
    """설명 생성 테스트"""

    def test_with_keywords(self):
        desc = _build_description(["demo", "tutorial"], "screen_recording")
        self.assertIn("화면 녹화", desc)
        self.assertIn("demo", desc)

    def test_no_keywords(self):
        desc = _build_description([], "stock_video")
        self.assertIn("일반", desc)


class TestGenerateBroll(unittest.TestCase):
    """B-roll 생성 통합 테스트"""

    def test_basic_generation(self):
        """기본 B-roll 제안 생성"""
        results = generate_broll("demo tutorial walkthrough")
        self.assertIsInstance(results, list)
        self.assertGreaterEqual(len(results), 1)
        self.assertLessEqual(len(results), 3)

    def test_result_type(self):
        """반환 타입 확인"""
        results = generate_broll("data statistics chart")
        for r in results:
            self.assertIsInstance(r, BrollSuggestion)

    def test_suggestion_fields(self):
        """BrollSuggestion 필드 확인"""
        results = generate_broll("process workflow pipeline")
        suggestion = results[0]
        self.assertIsInstance(suggestion.suggestion_id, str)
        self.assertIsInstance(suggestion.description, str)
        self.assertIn(suggestion.visual_type, VISUAL_TYPES)
        self.assertGreater(suggestion.duration_seconds, 0)
        self.assertGreaterEqual(suggestion.relevance, 0.0)
        self.assertLessEqual(suggestion.relevance, 1.0)
        self.assertIsInstance(suggestion.search_keywords, list)

    def test_empty_script_gap_raises(self):
        """빈 script_gap → ValueError"""
        with self.assertRaises(ValueError):
            generate_broll("")

    def test_whitespace_only_raises(self):
        """공백만 → ValueError"""
        with self.assertRaises(ValueError):
            generate_broll("   ")

    def test_with_context(self):
        """컨텍스트 포함 시 제안 생성"""
        results = generate_broll(
            "설치 방법 가이드",
            context="이 영상은 프로그램 설치 튜토리얼입니다"
        )
        self.assertGreaterEqual(len(results), 1)

    def test_primary_type_correct(self):
        """키워드에 맞는 주요 유형 추론"""
        results = generate_broll("demo setup install")
        primary = results[0]
        self.assertEqual(primary.visual_type, "screen_recording")

    def test_alternatives_different_type(self):
        """대안 제안은 주요 유형과 다른 유형"""
        results = generate_broll("data chart comparison")
        if len(results) > 1:
            primary_type = results[0].visual_type
            for alt in results[1:]:
                self.assertNotEqual(alt.visual_type, primary_type)

    def test_relevance_ordering(self):
        """주요 제안의 관련도가 대안보다 높거나 같음"""
        results = generate_broll("tutorial walkthrough demo")
        if len(results) > 1:
            self.assertGreaterEqual(results[0].relevance, results[1].relevance)


if __name__ == '__main__':
    unittest.main()
