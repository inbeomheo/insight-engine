"""구도 고정 변주 서비스 테스트"""

import unittest
from services.composition_variant_service import (
    Composition, Variant,
    create_composition, generate_variants, rank_variants,
)


class TestCompositionVariantService(unittest.TestCase):
    """구도 고정 변주 서비스 테스트"""

    def test_create_composition_valid(self):
        """유효한 구도 생성"""
        comp = create_composition(
            "centered",
            [{"id": "t1", "x": 0, "y": 0, "width": 100, "height": 50}],
            {"background": "#FFF", "text": "#000"},
        )
        self.assertEqual(comp.layout_type, "centered")
        self.assertEqual(len(comp.text_areas), 1)

    def test_create_composition_invalid_layout(self):
        """유효하지 않은 레이아웃"""
        with self.assertRaises(ValueError):
            create_composition("invalid", [], {})

    def test_create_composition_all_layouts(self):
        """모든 레이아웃 타입"""
        for lt in ("centered", "left-heavy", "right-heavy", "split", "diagonal"):
            comp = create_composition(lt, [], {})
            self.assertEqual(comp.layout_type, lt)

    def test_generate_variants_count(self):
        """변형 개수 = 텍스트 × 색상"""
        comp = create_composition("centered", [], {"bg": "#FFF"})
        texts = ["텍스트A", "텍스트B"]
        colors = [{"bg": "#000"}, {"bg": "#111"}, {"bg": "#222"}]
        variants = generate_variants(comp, texts, colors)
        self.assertEqual(len(variants), 6)  # 2 × 3

    def test_generate_variants_base_comp_id(self):
        """변형의 base_comp_id가 원본 구도 ID"""
        comp = create_composition("split", [], {})
        variants = generate_variants(comp, ["텍스트"], [{"bg": "#000"}])
        self.assertEqual(variants[0].base_comp_id, comp.comp_id)

    def test_generate_variants_preview_text_short(self):
        """짧은 텍스트 미리보기"""
        comp = create_composition("centered", [], {})
        variants = generate_variants(comp, ["짧은 텍스트"], [{}])
        self.assertEqual(variants[0].preview_text, "짧은 텍스트")

    def test_generate_variants_preview_text_long(self):
        """긴 텍스트 미리보기 (30자 + ...)"""
        comp = create_composition("centered", [], {})
        long_text = "A" * 50
        variants = generate_variants(comp, [long_text], [{}])
        self.assertTrue(variants[0].preview_text.endswith("..."))
        self.assertEqual(len(variants[0].preview_text), 33)  # 30 + "..."

    def test_generate_variants_empty_texts(self):
        """빈 텍스트 목록"""
        comp = create_composition("centered", [], {})
        variants = generate_variants(comp, [], [{"bg": "#000"}])
        self.assertEqual(len(variants), 0)

    def test_generate_variants_empty_colors(self):
        """빈 색상 목록"""
        comp = create_composition("centered", [], {})
        variants = generate_variants(comp, ["텍스트"], [])
        self.assertEqual(len(variants), 0)

    def test_rank_variants_order(self):
        """가독성 기반 순위 — 적정 길이가 상위"""
        comp = create_composition("centered", [], {})
        variants = generate_variants(
            comp,
            ["a" * 5, "적정 길이의 텍스트 문장입니다", "b" * 100],
            [{}],
        )
        ranked = rank_variants(variants)
        # 적정 길이(20~50자)가 최상위
        self.assertEqual(ranked[0].changes["text"], "적정 길이의 텍스트 문장입니다")

    def test_rank_variants_empty(self):
        """빈 변형 목록"""
        ranked = rank_variants([])
        self.assertEqual(ranked, [])

    def test_generate_variants_unique_ids(self):
        """각 변형은 고유 ID"""
        comp = create_composition("centered", [], {})
        variants = generate_variants(comp, ["A", "B"], [{"c": 1}])
        ids = {v.variant_id for v in variants}
        self.assertEqual(len(ids), 2)


if __name__ == "__main__":
    unittest.main()
