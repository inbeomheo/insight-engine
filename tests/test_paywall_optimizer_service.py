"""유료벽 최적화 서비스 테스트"""
import unittest

from services.paywall_optimizer_service import (
    PaywallRecommendation,
    calculate_free_ratio,
    optimize_paywall_position,
    _split_paragraphs,
    _extract_hook_text,
    _determine_target_ratio,
)


class TestSplitParagraphs(unittest.TestCase):
    """문단 분리 테스트"""

    def test_basic_split(self):
        content = "첫 번째 문단입니다.\n\n두 번째 문단입니다."
        result = _split_paragraphs(content)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "첫 번째 문단입니다.")

    def test_empty_content(self):
        self.assertEqual(_split_paragraphs(""), [])

    def test_single_paragraph(self):
        result = _split_paragraphs("하나의 문단만 있습니다.")
        self.assertEqual(len(result), 1)

    def test_multiple_newlines(self):
        content = "문단1\n\n\n\n문단2\n\n문단3"
        result = _split_paragraphs(content)
        self.assertEqual(len(result), 3)


class TestExtractHookText(unittest.TestCase):
    """훅 텍스트 추출 테스트"""

    def test_question_sentence_priority(self):
        """질문형 문장이 우선 선택되어야 한다"""
        paragraph = "이것은 일반 문장입니다. 왜 이렇게 될까요? 마지막 문장입니다."
        result = _extract_hook_text(paragraph)
        self.assertIn("왜 이렇게 될까요", result)

    def test_hook_keyword_priority(self):
        """질문이 없으면 핵심 키워드 문장이 선택되어야 한다"""
        paragraph = "시작 문장. 가장 중요한 비밀을 알려드립니다. 끝."
        result = _extract_hook_text(paragraph)
        self.assertIn("비밀", result)

    def test_last_sentence_fallback(self):
        """질문도 키워드도 없으면 마지막 문장 반환"""
        paragraph = "일반 문장 하나. 일반 문장 둘. 일반 문장 셋"
        result = _extract_hook_text(paragraph)
        self.assertIn("셋", result)

    def test_empty_paragraph(self):
        result = _extract_hook_text("")
        self.assertEqual(result, "")


class TestDetermineTargetRatio(unittest.TestCase):
    """목표 비율 결정 테스트"""

    def test_no_analytics(self):
        ratio, reason = _determine_target_ratio(None)
        self.assertAlmostEqual(ratio, 0.4)
        self.assertIn("분석 데이터 없음", reason)

    def test_high_bounce_rate(self):
        ratio, _ = _determine_target_ratio({'bounce_rate': 0.7})
        self.assertAlmostEqual(ratio, 0.25)

    def test_high_engagement(self):
        ratio, _ = _determine_target_ratio({'engagement': 0.8})
        self.assertAlmostEqual(ratio, 0.6)

    def test_moderate_bounce_rate(self):
        ratio, _ = _determine_target_ratio({'bounce_rate': 0.5})
        self.assertAlmostEqual(ratio, 0.3)

    def test_moderate_engagement(self):
        ratio, _ = _determine_target_ratio({'engagement': 0.5})
        self.assertAlmostEqual(ratio, 0.5)

    def test_default_fallback(self):
        """특별한 조건이 아니면 기본 40%"""
        ratio, _ = _determine_target_ratio({'bounce_rate': 0.2, 'engagement': 0.2})
        self.assertAlmostEqual(ratio, 0.4)


class TestCalculateFreeRatio(unittest.TestCase):
    """무료 비율 계산 테스트"""

    def test_basic_ratio(self):
        content = "a" * 100
        ratio = calculate_free_ratio(content, 40)
        self.assertAlmostEqual(ratio, 0.4)

    def test_zero_position(self):
        ratio = calculate_free_ratio("abc", 0)
        self.assertAlmostEqual(ratio, 0.0)

    def test_full_position(self):
        ratio = calculate_free_ratio("abc", 3)
        self.assertAlmostEqual(ratio, 1.0)

    def test_empty_content(self):
        ratio = calculate_free_ratio("", 5)
        self.assertAlmostEqual(ratio, 0.0)

    def test_position_beyond_content(self):
        """position이 콘텐츠보다 크면 1.0으로 클램핑"""
        ratio = calculate_free_ratio("abc", 100)
        self.assertAlmostEqual(ratio, 1.0)

    def test_negative_position(self):
        """음수 position은 0으로 클램핑"""
        ratio = calculate_free_ratio("abc", -5)
        self.assertAlmostEqual(ratio, 0.0)


class TestOptimizePaywallPosition(unittest.TestCase):
    """유료벽 최적 위치 추천 통합 테스트"""

    def test_returns_recommendation_type(self):
        content = "문단1 내용입니다.\n\n문단2 내용입니다.\n\n문단3 내용입니다."
        result = optimize_paywall_position(content)
        self.assertIsInstance(result, PaywallRecommendation)

    def test_empty_content(self):
        result = optimize_paywall_position("")
        self.assertEqual(result.position, 0)
        self.assertAlmostEqual(result.free_ratio, 0.0)

    def test_whitespace_only_content(self):
        result = optimize_paywall_position("   \n\n  ")
        self.assertEqual(result.position, 0)

    def test_position_within_bounds(self):
        content = "문단1\n\n문단2\n\n문단3\n\n문단4\n\n문단5"
        result = optimize_paywall_position(content)
        self.assertGreaterEqual(result.position, 0)
        self.assertLessEqual(result.position, len(content))

    def test_free_ratio_in_range(self):
        content = "문단1 내용.\n\n문단2 내용.\n\n문단3 내용.\n\n문단4 내용."
        result = optimize_paywall_position(content)
        self.assertGreaterEqual(result.free_ratio, 0.0)
        self.assertLessEqual(result.free_ratio, 1.0)

    def test_high_bounce_moves_paywall_forward(self):
        """높은 이탈률은 유료벽을 앞으로 이동"""
        content = "가" * 50 + "\n\n" + "나" * 50 + "\n\n" + "다" * 50 + "\n\n" + "라" * 50
        normal = optimize_paywall_position(content)
        high_bounce = optimize_paywall_position(content, {'bounce_rate': 0.8})
        self.assertLessEqual(high_bounce.free_ratio, normal.free_ratio)

    def test_high_engagement_moves_paywall_backward(self):
        """높은 참여도는 유료벽을 뒤로 이동"""
        content = "가" * 50 + "\n\n" + "나" * 50 + "\n\n" + "다" * 50 + "\n\n" + "라" * 50
        normal = optimize_paywall_position(content)
        high_engage = optimize_paywall_position(content, {'engagement': 0.9})
        self.assertGreaterEqual(high_engage.free_ratio, normal.free_ratio)

    def test_hook_text_not_empty(self):
        content = "서론입니다.\n\n본론입니다.\n\n결론입니다."
        result = optimize_paywall_position(content)
        self.assertTrue(len(result.hook_text) > 0)

    def test_paragraph_index_valid(self):
        content = "A\n\nB\n\nC\n\nD\n\nE"
        result = optimize_paywall_position(content)
        self.assertGreaterEqual(result.paragraph_index, 0)
        self.assertLess(result.paragraph_index, 5)

    def test_reason_not_empty(self):
        content = "콘텐츠입니다.\n\n두 번째 문단입니다."
        result = optimize_paywall_position(content)
        self.assertTrue(len(result.reason) > 0)


if __name__ == '__main__':
    unittest.main()
