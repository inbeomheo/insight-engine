"""관할권 렌더러 서비스 테스트."""

import unittest
from services.jurisdiction_renderer_service import (
    JurisdictionRule,
    get_applicable_rules,
    render_for_jurisdiction,
    check_compliance,
    add_age_gate,
)


class TestJurisdictionRendererService(unittest.TestCase):
    """JurisdictionRendererService 단위 테스트."""

    def setUp(self):
        """테스트용 관할권 규칙."""
        self.eu_rule = JurisdictionRule(
            jurisdiction="EU",
            content_type="blog",
            required_disclaimers=["GDPR 준수 고지", "쿠키 동의 필요"],
            blocked_content=["무허가 의료 정보"],
            age_gate=True,
        )
        self.us_rule = JurisdictionRule(
            jurisdiction="US",
            content_type="blog",
            required_disclaimers=["CCPA 고지"],
            blocked_content=[],
            age_gate=False,
        )
        self.global_rule = JurisdictionRule(
            jurisdiction="global",
            content_type="*",
            required_disclaimers=["면책 조항: AI 생성 콘텐츠"],
            blocked_content=[],
            age_gate=False,
        )
        self.kr_rule = JurisdictionRule(
            jurisdiction="KR",
            content_type="blog",
            required_disclaimers=["개인정보처리방침 고지"],
            blocked_content=["도박 광고"],
            age_gate=False,
        )
        self.rules = [self.eu_rule, self.us_rule, self.global_rule, self.kr_rule]

    def test_get_applicable_rules_eu(self):
        """EU 관할권에 EU + global 규칙이 적용된다."""
        applicable = get_applicable_rules("EU", "blog", self.rules)
        jurisdictions = {r.jurisdiction for r in applicable}
        self.assertIn("EU", jurisdictions)
        self.assertIn("global", jurisdictions)
        self.assertNotIn("US", jurisdictions)

    def test_get_applicable_rules_global_always(self):
        """global 규칙은 항상 포함된다."""
        applicable = get_applicable_rules("JP", "blog", self.rules)
        self.assertTrue(any(r.jurisdiction == "global" for r in applicable))

    def test_get_applicable_rules_type_filter(self):
        """콘텐츠 유형이 일치해야 적용된다."""
        applicable = get_applicable_rules("EU", "video", self.rules)
        # EU blog 규칙은 video에 불일치, global * 규칙만 적용
        self.assertTrue(all(r.content_type == "*" for r in applicable))

    def test_render_adds_disclaimers(self):
        """면책조항이 추가된다."""
        content = {"text": "테스트 콘텐츠", "type": "blog"}
        result = render_for_jurisdiction(content, "EU", self.rules)
        self.assertIn("GDPR 준수 고지", result["disclaimers"])
        self.assertIn("면책 조항: AI 생성 콘텐츠", result["disclaimers"])

    def test_render_removes_blocked_content(self):
        """차단 키워드가 [BLOCKED]로 대체된다."""
        content = {"text": "이 글은 무허가 의료 정보를 포함합니다", "type": "blog"}
        result = render_for_jurisdiction(content, "EU", self.rules)
        self.assertIn("[BLOCKED]", result["text"])
        self.assertNotIn("무허가 의료 정보", result["text"])

    def test_render_adds_age_gate(self):
        """EU 콘텐츠에 age_gate 플래그가 추가된다."""
        content = {"text": "테스트", "type": "blog"}
        result = render_for_jurisdiction(content, "EU", self.rules)
        self.assertTrue(result.get("age_gate"))

    def test_render_no_age_gate_us(self):
        """US 콘텐츠에는 age_gate가 없다."""
        content = {"text": "test", "type": "blog"}
        result = render_for_jurisdiction(content, "US", self.rules)
        self.assertNotIn("age_gate", result)

    def test_render_dedup_disclaimers(self):
        """중복 면책조항이 제거된다."""
        dup_rule = JurisdictionRule(
            jurisdiction="global", content_type="*",
            required_disclaimers=["면책 조항: AI 생성 콘텐츠"], blocked_content=[], age_gate=False,
        )
        rules = [self.global_rule, dup_rule]
        content = {"text": "test", "type": "blog"}
        result = render_for_jurisdiction(content, "US", rules)
        count = result["disclaimers"].count("면책 조항: AI 생성 콘텐츠")
        self.assertEqual(count, 1)

    def test_check_compliance_no_violation(self):
        """위반 없는 콘텐츠."""
        content = {"text": "깨끗한 콘텐츠입니다"}
        violations = check_compliance(content, self.rules)
        self.assertEqual(violations, [])

    def test_check_compliance_with_violation(self):
        """차단 키워드 포함 시 위반 목록 반환."""
        content = {"text": "이 글은 도박 광고를 포함합니다"}
        violations = check_compliance(content, self.rules)
        self.assertTrue(len(violations) > 0)
        self.assertTrue(any("도박 광고" in v for v in violations))

    def test_add_age_gate_eu(self):
        """EU 연령 확인은 16세."""
        result = add_age_gate({"text": "test"}, "EU")
        self.assertTrue(result["age_gate"])
        self.assertEqual(result["min_age"], 16)

    def test_add_age_gate_us(self):
        """US 연령 확인은 13세."""
        result = add_age_gate({"text": "test"}, "US")
        self.assertEqual(result["min_age"], 13)

    def test_add_age_gate_kr(self):
        """KR 연령 확인은 14세."""
        result = add_age_gate({"text": "test"}, "KR")
        self.assertEqual(result["min_age"], 14)

    def test_add_age_gate_unknown_jurisdiction(self):
        """알 수 없는 관할권은 기본 13세."""
        result = add_age_gate({"text": "test"}, "XX")
        self.assertEqual(result["min_age"], 13)

    def test_render_preserves_original_fields(self):
        """원본 콘텐츠의 추가 필드가 보존된다."""
        content = {"text": "test", "type": "blog", "author": "홍길동"}
        result = render_for_jurisdiction(content, "KR", self.rules)
        self.assertEqual(result["author"], "홍길동")


if __name__ == "__main__":
    unittest.main()
