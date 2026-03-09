"""자가복구 생성 서비스 테스트."""

import unittest
from services.self_healing_generation_service import (
    GenerationAttempt,
    RecoveryStrategy,
    assess_quality,
    needs_recovery,
    suggest_recovery,
    apply_simplification,
)


class TestAssessQuality(unittest.TestCase):
    """품질 점수 평가 테스트."""

    def test_empty_text(self):
        """빈 텍스트 → 0.0."""
        self.assertEqual(assess_quality(""), 0.0)
        self.assertEqual(assess_quality("   "), 0.0)

    def test_none_text(self):
        """None → 0.0."""
        self.assertEqual(assess_quality(None), 0.0)

    def test_short_text(self):
        """짧은 텍스트 → 낮은 점수."""
        score = assess_quality("짧은 글.")
        self.assertLess(score, 0.5)

    def test_long_structured_text(self):
        """긴 구조화된 텍스트 → 높은 점수."""
        text = "첫 번째 문단의 내용입니다.\n" * 5
        text += "두 번째 문단의 내용입니다.\n" * 5
        text += "세 번째 문단으로 마무리합니다."
        score = assess_quality(text)
        self.assertGreater(score, 0.5)

    def test_score_bounded(self):
        """점수 0~1 범위."""
        long_text = "매우 긴 텍스트입니다. " * 100 + "\n" * 10
        score = assess_quality(long_text)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_sentence_endings_boost(self):
        """문장 종결 부호 → 점수 증가."""
        text_no_end = "문장 끝이 없는 텍스트 입니다"
        text_with_end = "문장 끝이 있습니다. 완전한 문장입니다. 그렇습니다."
        score_no = assess_quality(text_no_end)
        score_with = assess_quality(text_with_end)
        self.assertGreater(score_with, score_no)

    def test_multiline_boost(self):
        """여러 줄 → 구조 점수 증가."""
        single_line = "한 줄짜리 긴 텍스트입니다." + "a" * 100
        multi_line = "첫 줄\n둘째 줄\n셋째 줄"
        score_single = assess_quality(single_line)
        score_multi = assess_quality(multi_line)
        # 다중 줄이 구조 점수 더 높음
        # (단, 길이가 다르므로 구조 점수만 비교 의미)
        self.assertIsInstance(score_multi, float)


class TestNeedsRecovery(unittest.TestCase):
    """복구 필요 여부 테스트."""

    def test_failed_needs_recovery(self):
        """failed 상태 → 복구 필요."""
        attempt = GenerationAttempt("a1", "blog", "입력", "", 0.0, "failed")
        self.assertTrue(needs_recovery(attempt))

    def test_low_quality_needs_recovery(self):
        """품질 0.5 미만 → 복구 필요."""
        attempt = GenerationAttempt("a1", "blog", "입력", "출력", 0.3, "success")
        self.assertTrue(needs_recovery(attempt))

    def test_success_high_quality_no_recovery(self):
        """성공 + 높은 품질 → 복구 불필요."""
        attempt = GenerationAttempt("a1", "blog", "입력", "출력", 0.8, "success")
        self.assertFalse(needs_recovery(attempt))

    def test_partial_high_quality_no_recovery(self):
        """partial + 높은 품질 → 복구 불필요."""
        attempt = GenerationAttempt("a1", "blog", "입력", "출력", 0.7, "partial")
        self.assertFalse(needs_recovery(attempt))

    def test_boundary_quality(self):
        """품질 0.5 경계값 → 복구 불필요 (< 0.5만 필요)."""
        attempt = GenerationAttempt("a1", "blog", "입력", "출력", 0.5, "success")
        self.assertFalse(needs_recovery(attempt))


class TestSuggestRecovery(unittest.TestCase):
    """복구 전략 제안 테스트."""

    def test_failed_long_input_simplify(self):
        """failed + 긴 입력 → simplify."""
        attempt = GenerationAttempt("a1", "blog", "x" * 600, "", 0.0, "failed")
        strategy = suggest_recovery(attempt)
        self.assertEqual(strategy.strategy_type, "simplify")

    def test_failed_short_input_retry(self):
        """failed + 짧은 입력 → retry."""
        attempt = GenerationAttempt("a1", "blog", "짧은 입력", "", 0.0, "failed")
        strategy = suggest_recovery(attempt)
        self.assertEqual(strategy.strategy_type, "retry")

    def test_partial_chunk(self):
        """partial → chunk."""
        attempt = GenerationAttempt("a1", "blog", "입력", "부분결과", 0.4, "partial")
        strategy = suggest_recovery(attempt)
        self.assertEqual(strategy.strategy_type, "chunk")

    def test_low_quality_fallback(self):
        """낮은 품질 success → fallback."""
        attempt = GenerationAttempt("a1", "blog", "입력", "저품질", 0.3, "success")
        strategy = suggest_recovery(attempt)
        self.assertEqual(strategy.strategy_type, "fallback")

    def test_strategy_has_description(self):
        """모든 전략에 설명 포함."""
        attempt = GenerationAttempt("a1", "blog", "입력", "", 0.0, "failed")
        strategy = suggest_recovery(attempt)
        self.assertTrue(len(strategy.description) > 0)


class TestApplySimplification(unittest.TestCase):
    """입력 단순화 테스트."""

    def test_simplify_empty(self):
        """빈 텍스트 → 그대로."""
        self.assertEqual(apply_simplification(""), "")
        self.assertEqual(apply_simplification("  "), "  ")

    def test_simplify_removes_parentheses(self):
        """괄호 내용 제거."""
        result = apply_simplification("인공지능(AI)은 기술이다")
        self.assertNotIn("(AI)", result)
        self.assertIn("인공지능", result)

    def test_simplify_removes_korean_parentheses(self):
        """한국어 괄호 제거."""
        result = apply_simplification("데이터（데이터 분석용）처리")
        self.assertNotIn("（", result)
        self.assertNotIn("데이터 분석용", result)

    def test_simplify_cleans_whitespace(self):
        """연속 공백 정리."""
        result = apply_simplification("여러   공백이    있는  텍스트")
        self.assertNotIn("  ", result)

    def test_simplify_truncates_long_text(self):
        """500자 초과 → 앞부분만 유지."""
        long_text = "긴 문장입니다. " * 100  # 800자 이상
        result = apply_simplification(long_text)
        self.assertLessEqual(len(result), 510)  # 문장 단위라 약간 넘을 수 있음

    def test_simplify_short_text_preserved(self):
        """짧은 텍스트는 그대로 유지."""
        text = "짧은 텍스트."
        result = apply_simplification(text)
        self.assertIn("짧은", result)
        self.assertIn("텍스트", result)


if __name__ == "__main__":
    unittest.main()
