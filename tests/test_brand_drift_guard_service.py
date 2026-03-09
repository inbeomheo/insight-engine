"""
브랜드 보이스 드리프트 감지 + 가드레일 적용 서비스 테스트
"""
import unittest

from services.brand_drift_guard_service import (
    BrandRules,
    ParagraphDrift,
    Violation,
    score_drift,
    apply_guardrails,
    check_violations,
    get_drift_summary,
)


def _make_rules(**overrides) -> BrandRules:
    """테스트용 BrandRules 팩토리."""
    defaults = {
        'brand_name': 'TestBrand',
        'tone': '전문적',
        'forbidden_words': ['놀라운', '혁신적', '최고의'],
        'required_cta': '',
        'max_sentence_length': 0,
        'preferred_words': [],
    }
    defaults.update(overrides)
    return BrandRules(**defaults)


class TestScoreDriftClean(unittest.TestCase):
    """위반 없는 콘텐츠에 대한 점수 검증."""

    def test_score_drift_clean(self):
        content = "데이터를 분석하여 검토한 결과를 보고합니다.\n평가 기준에 따라 수행했습니다."
        rules = _make_rules()
        drifts = score_drift(content, rules)

        self.assertEqual(len(drifts), 2)
        for d in drifts:
            self.assertEqual(d.drift_score, 0.0)
            self.assertEqual(d.violations, [])


class TestScoreDriftForbiddenWord(unittest.TestCase):
    """금지어 포함 시 점수 상승 검증."""

    def test_score_drift_forbidden_word(self):
        content = "이것은 놀라운 결과입니다."
        rules = _make_rules()
        drifts = score_drift(content, rules)

        self.assertEqual(len(drifts), 1)
        self.assertGreaterEqual(drifts[0].drift_score, 30.0)
        self.assertTrue(any('금지어' in v for v in drifts[0].violations))


class TestScoreDriftMultipleViolations(unittest.TestCase):
    """복합 위반 시 점수 누적 검증."""

    def test_score_drift_multiple_violations(self):
        # 금지어(+30) + 톤 불일치(+25) = 55점 이상
        content = "대박 놀라운 성과입니다 ㅋㅋ"
        rules = _make_rules()
        drifts = score_drift(content, rules)

        self.assertEqual(len(drifts), 1)
        self.assertGreaterEqual(drifts[0].drift_score, 55.0)
        self.assertGreater(len(drifts[0].violations), 1)


class TestScoreDriftEmpty(unittest.TestCase):
    """빈 콘텐츠 처리."""

    def test_score_drift_empty(self):
        self.assertEqual(score_drift("", _make_rules()), [])
        self.assertEqual(score_drift("   ", _make_rules()), [])
        self.assertEqual(score_drift(None, _make_rules()), [])


class TestApplyGuardrailsBasic(unittest.TestCase):
    """기본 규칙 주입 확인."""

    def test_apply_guardrails_basic(self):
        prompt = "다음 내용을 작성하세요."
        rules = _make_rules()
        result = apply_guardrails(prompt, rules)

        self.assertIn("브랜드 가드레일", result)
        self.assertIn("TestBrand", result)
        self.assertIn("전문적", result)
        self.assertTrue(result.startswith(prompt))


class TestApplyGuardrailsWithCta(unittest.TestCase):
    """CTA 포함 주입 확인."""

    def test_apply_guardrails_with_cta(self):
        prompt = "블로그 글을 작성하세요."
        rules = _make_rules(required_cta="지금 바로 시작하세요!")
        result = apply_guardrails(prompt, rules)

        self.assertIn("지금 바로 시작하세요!", result)
        self.assertIn("필수 CTA", result)


class TestApplyGuardrailsForbidden(unittest.TestCase):
    """금지어 목록 주입 확인."""

    def test_apply_guardrails_forbidden(self):
        prompt = "콘텐츠를 생성하세요."
        rules = _make_rules(forbidden_words=['놀라운', '혁신적', '게임체인저'])
        result = apply_guardrails(prompt, rules)

        self.assertIn("금지어", result)
        self.assertIn("놀라운", result)
        self.assertIn("혁신적", result)
        self.assertIn("게임체인저", result)


class TestCheckViolationsNone(unittest.TestCase):
    """위반 없는 콘텐츠."""

    def test_check_violations_none(self):
        content = "데이터를 분석하여 결과를 검토했습니다."
        rules = _make_rules()
        violations = check_violations(content, rules)
        self.assertEqual(violations, [])


class TestCheckViolationsForbidden(unittest.TestCase):
    """금지어 위반 검출."""

    def test_check_violations_forbidden(self):
        content = "이것은 놀라운 혁신적 제품입니다."
        rules = _make_rules()
        violations = check_violations(content, rules)

        forbidden_violations = [v for v in violations if v.violation_type == "forbidden_word"]
        self.assertGreaterEqual(len(forbidden_violations), 2)
        self.assertTrue(all(v.severity == "high" for v in forbidden_violations))


class TestCheckViolationsSentenceLength(unittest.TestCase):
    """문장 길이 위반 검출."""

    def test_check_violations_sentence_length(self):
        # 100자 초과 문장 생성
        long_sentence = "이것은 " + "매우 긴 " * 20 + "문장입니다."
        rules = _make_rules(max_sentence_length=50)
        violations = check_violations(long_sentence, rules)

        length_violations = [v for v in violations if v.violation_type == "sentence_too_long"]
        self.assertGreaterEqual(len(length_violations), 1)
        self.assertTrue(all(v.severity == "low" for v in length_violations))


class TestCheckViolationsSeverity(unittest.TestCase):
    """심각도 분류 검증."""

    def test_check_violations_severity(self):
        # 금지어(high) + 톤 불일치(medium) + CTA 누락(high)
        content = "대박 놀라운 성과입니다 ㅋㅋ"
        rules = _make_rules(required_cta="문의하세요")
        violations = check_violations(content, rules)

        severities = {v.severity for v in violations}
        self.assertIn("high", severities)
        self.assertIn("medium", severities)

        # CTA 누락은 high
        cta_violations = [v for v in violations if v.violation_type == "cta_missing"]
        self.assertEqual(len(cta_violations), 1)
        self.assertEqual(cta_violations[0].severity, "high")


class TestGetDriftSummary(unittest.TestCase):
    """요약 통계 검증."""

    def test_get_drift_summary(self):
        drifts = [
            ParagraphDrift(0, "첫 번째 문단", 30.0, ["금지어 \"놀라운\" 포함"]),
            ParagraphDrift(1, "두 번째 문단", 0.0, []),
            ParagraphDrift(2, "세 번째 문단", 55.0, ["금지어 \"혁신적\" 포함", "톤 불일치 표현 \"대박\""]),
        ]
        summary = get_drift_summary(drifts)

        # 평균 점수: (30 + 0 + 55) / 3 = 28.3
        self.assertAlmostEqual(summary['average_score'], 28.3, places=1)

        # 최고 이탈 문단: index 2
        self.assertEqual(summary['max_drift_paragraph']['index'], 2)
        self.assertEqual(summary['max_drift_paragraph']['score'], 55.0)

        # 전체 위반 수: 3
        self.assertEqual(summary['total_violations'], 3)

        # 위반 유형별 집계
        self.assertEqual(summary['violation_summary'].get('forbidden_word', 0), 2)
        self.assertEqual(summary['violation_summary'].get('tone_mismatch', 0), 1)

    def test_get_drift_summary_empty(self):
        summary = get_drift_summary([])

        self.assertEqual(summary['average_score'], 0.0)
        self.assertIsNone(summary['max_drift_paragraph'])
        self.assertEqual(summary['total_violations'], 0)
        self.assertEqual(summary['violation_summary'], {})


class TestScoreDriftCap(unittest.TestCase):
    """점수 상한 100 검증."""

    def test_score_drift_capped_at_100(self):
        # 금지어 3개(+90) + 톤 불일치 2개(+50) = 140 → 100으로 캡
        content = "놀라운 혁신적 최고의 성과 대박 ㅋㅋ"
        rules = _make_rules()
        drifts = score_drift(content, rules)

        self.assertEqual(len(drifts), 1)
        self.assertEqual(drifts[0].drift_score, 100.0)


class TestApplyGuardrailsSentenceLength(unittest.TestCase):
    """문장 길이 제한 주입 확인."""

    def test_apply_guardrails_sentence_length(self):
        prompt = "콘텐츠를 작성하세요."
        rules = _make_rules(max_sentence_length=80)
        result = apply_guardrails(prompt, rules)

        self.assertIn("문장 길이 제한", result)
        self.assertIn("80", result)


class TestApplyGuardrailsPreferredWords(unittest.TestCase):
    """선호 표현 주입 확인."""

    def test_apply_guardrails_preferred_words(self):
        prompt = "콘텐츠를 작성하세요."
        rules = _make_rules(preferred_words=['분석', '검토', '평가'])
        result = apply_guardrails(prompt, rules)

        self.assertIn("선호 표현", result)
        self.assertIn("분석", result)


class TestCheckViolationsCtaMissing(unittest.TestCase):
    """CTA 누락 검출."""

    def test_cta_missing(self):
        content = "좋은 결과를 보여드리겠습니다."
        rules = _make_rules(required_cta="지금 신청하세요")
        violations = check_violations(content, rules)

        cta = [v for v in violations if v.violation_type == "cta_missing"]
        self.assertEqual(len(cta), 1)
        self.assertEqual(cta[0].location, "entire content")

    def test_cta_present(self):
        content = "좋은 결과를 보여드리겠습니다. 지금 신청하세요!"
        rules = _make_rules(required_cta="지금 신청하세요")
        violations = check_violations(content, rules)

        cta = [v for v in violations if v.violation_type == "cta_missing"]
        self.assertEqual(len(cta), 0)


class TestCheckViolationsEmptyContent(unittest.TestCase):
    """빈 콘텐츠에서 위반 검사."""

    def test_empty(self):
        self.assertEqual(check_violations("", _make_rules()), [])
        self.assertEqual(check_violations(None, _make_rules()), [])


if __name__ == '__main__':
    unittest.main()
