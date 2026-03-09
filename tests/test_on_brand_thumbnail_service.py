"""온브랜드 썸네일 서비스 테스트"""

import unittest
from services.on_brand_thumbnail_service import (
    BrandGuideline, ThumbnailSpec,
    generate_spec, validate_brand_compliance, suggest_variations,
)


class TestOnBrandThumbnailService(unittest.TestCase):
    """온브랜드 썸네일 서비스 테스트"""

    def _make_guideline(self, **overrides):
        defaults = {
            "brand_colors": ["#FF0000", "#FFFFFF", "#000000"],
            "font_family": "Pretendard",
            "logo_position": "top-left",
            "style": "minimal",
        }
        defaults.update(overrides)
        return BrandGuideline(**defaults)

    def test_generate_spec_basic(self):
        """기본 스펙 생성"""
        g = self._make_guideline()
        spec = generate_spec("테스트 제목", g)
        self.assertEqual(spec.title_text, "테스트 제목")
        self.assertEqual(spec.font, "Pretendard")
        self.assertEqual(spec.logo_position, "top-left")
        self.assertIn("primary", spec.colors)

    def test_generate_spec_16_9(self):
        """16:9 비율"""
        g = self._make_guideline()
        spec = generate_spec("제목", g, "16:9")
        self.assertEqual(spec.dimensions["width"], 1280)
        self.assertEqual(spec.dimensions["height"], 720)

    def test_generate_spec_1_1(self):
        """1:1 비율"""
        g = self._make_guideline()
        spec = generate_spec("제목", g, "1:1")
        self.assertEqual(spec.dimensions["width"], 1080)
        self.assertEqual(spec.dimensions["height"], 1080)

    def test_generate_spec_unknown_ratio_fallback(self):
        """알 수 없는 비율은 16:9 폴백"""
        g = self._make_guideline()
        spec = generate_spec("제목", g, "21:9")
        self.assertEqual(spec.dimensions["width"], 1280)

    def test_generate_spec_title_with_colon(self):
        """콜론이 있는 제목에서 부제목 분리"""
        g = self._make_guideline()
        spec = generate_spec("메인: 서브 타이틀", g)
        self.assertEqual(spec.title_text, "메인")
        self.assertEqual(spec.subtitle_text, "서브 타이틀")

    def test_generate_spec_style_layout(self):
        """스타일에 따른 레이아웃"""
        for style, expected in [("minimal", "centered"), ("bold", "split"), ("playful", "left-aligned")]:
            g = self._make_guideline(style=style)
            spec = generate_spec("제목", g)
            self.assertEqual(spec.layout, expected, f"스타일 {style}")

    def test_validate_brand_compliance_pass(self):
        """가이드라인 준수"""
        g = self._make_guideline()
        spec = generate_spec("제목", g)
        issues = validate_brand_compliance(spec, g)
        self.assertEqual(issues, [])

    def test_validate_brand_compliance_font_mismatch(self):
        """폰트 불일치 감지"""
        g = self._make_guideline()
        spec = generate_spec("제목", g)
        spec.font = "Arial"
        issues = validate_brand_compliance(spec, g)
        self.assertTrue(any("폰트" in i for i in issues))

    def test_validate_brand_compliance_logo_mismatch(self):
        """로고 위치 불일치 감지"""
        g = self._make_guideline()
        spec = generate_spec("제목", g)
        spec.logo_position = "bottom-right"
        issues = validate_brand_compliance(spec, g)
        self.assertTrue(any("로고" in i for i in issues))

    def test_validate_brand_compliance_color_mismatch(self):
        """색상 불일치 감지"""
        g = self._make_guideline()
        spec = generate_spec("제목", g)
        spec.colors["primary"] = "#00FF00"
        issues = validate_brand_compliance(spec, g)
        self.assertTrue(any("색상" in i for i in issues))

    def test_suggest_variations_count(self):
        """변형 개수"""
        g = self._make_guideline()
        spec = generate_spec("제목", g)
        variations = suggest_variations(spec, 5)
        self.assertEqual(len(variations), 5)

    def test_suggest_variations_different_ids(self):
        """변형은 서로 다른 ID"""
        g = self._make_guideline()
        spec = generate_spec("제목", g)
        variations = suggest_variations(spec, 3)
        ids = {v.spec_id for v in variations}
        self.assertEqual(len(ids), 3)

    def test_suggest_variations_color_invert(self):
        """첫 번째 변형은 색상 반전"""
        g = self._make_guideline()
        spec = generate_spec("제목", g)
        variations = suggest_variations(spec, 1)
        v = variations[0]
        # 색상 반전: primary/secondary 교환
        self.assertEqual(v.colors["primary"], spec.colors["secondary"])
        self.assertEqual(v.colors["secondary"], spec.colors["primary"])

    def test_generate_spec_empty_brand_colors(self):
        """빈 브랜드 색상 처리"""
        g = self._make_guideline(brand_colors=[])
        spec = generate_spec("제목", g)
        self.assertEqual(spec.colors["primary"], "#000000")


if __name__ == "__main__":
    unittest.main()
