"""
런타임 조립 서비스 테스트
"""

import unittest

from services.runtime_assembly_service import (
    ContentModule,
    AssembledPage,
    register_module,
    evaluate_conditions,
    assemble_page,
    get_variants,
)


class TestRegisterModule(unittest.TestCase):
    """모듈 등록 테스트"""

    def test_register_new(self):
        """새 모듈 등록"""
        modules = []
        m = ContentModule("m1", "header", "헤더 콘텐츠", priority=10)
        modules = register_module(modules, m)
        self.assertEqual(len(modules), 1)
        self.assertEqual(modules[0].module_id, "m1")

    def test_register_replace_existing(self):
        """기존 모듈 교체"""
        modules = []
        m1 = ContentModule("m1", "header", "원본", priority=1)
        modules = register_module(modules, m1)
        m2 = ContentModule("m1", "header", "교체됨", priority=5)
        modules = register_module(modules, m2)
        self.assertEqual(len(modules), 1)
        self.assertEqual(modules[0].content, "교체됨")
        self.assertEqual(modules[0].priority, 5)

    def test_register_multiple(self):
        """여러 모듈 등록"""
        modules = []
        for i in range(5):
            m = ContentModule(f"m{i}", "body", f"콘텐츠 {i}")
            modules = register_module(modules, m)
        self.assertEqual(len(modules), 5)


class TestEvaluateConditions(unittest.TestCase):
    """조건 평가 테스트"""

    def test_no_conditions(self):
        """조건 없음 — 항상 통과"""
        m = ContentModule("m1", "header", "콘텐츠")
        self.assertTrue(evaluate_conditions(m, {}))

    def test_condition_match(self):
        """조건 매칭"""
        m = ContentModule("m1", "header", "콘텐츠", conditions={"theme": "dark"})
        self.assertTrue(evaluate_conditions(m, {"theme": "dark"}))

    def test_condition_mismatch(self):
        """조건 불일치"""
        m = ContentModule("m1", "header", "콘텐츠", conditions={"theme": "dark"})
        self.assertFalse(evaluate_conditions(m, {"theme": "light"}))

    def test_condition_missing_key(self):
        """컨텍스트에 키 없음"""
        m = ContentModule("m1", "header", "콘텐츠", conditions={"theme": "dark"})
        self.assertFalse(evaluate_conditions(m, {}))

    def test_multiple_conditions(self):
        """여러 조건 (AND)"""
        m = ContentModule("m1", "header", "콘텐츠",
                          conditions={"theme": "dark", "locale": "ko"})
        self.assertTrue(evaluate_conditions(m, {"theme": "dark", "locale": "ko"}))
        self.assertFalse(evaluate_conditions(m, {"theme": "dark", "locale": "en"}))

    def test_list_condition(self):
        """리스트 조건 (OR)"""
        m = ContentModule("m1", "header", "콘텐츠",
                          conditions={"locale": ["ko", "ja"]})
        self.assertTrue(evaluate_conditions(m, {"locale": "ko"}))
        self.assertTrue(evaluate_conditions(m, {"locale": "ja"}))
        self.assertFalse(evaluate_conditions(m, {"locale": "en"}))


class TestAssemblePage(unittest.TestCase):
    """페이지 조립 테스트"""

    def setUp(self):
        self.modules = [
            ContentModule("m1", "header", "헤더", priority=10),
            ContentModule("m2", "body", "본문", priority=5),
            ContentModule("m3", "footer", "푸터", priority=1),
            ContentModule("m4", "cta", "CTA (다크 전용)", priority=8,
                          conditions={"theme": "dark"}),
            ContentModule("m5", "sidebar", "사이드바 (라이트 전용)", priority=3,
                          conditions={"theme": "light"}),
        ]

    def test_assemble_basic(self):
        """기본 조립 (조건 없는 모듈만)"""
        page = assemble_page(self.modules, {})
        # 조건 없는 3개만 통과
        self.assertEqual(len(page.modules), 3)

    def test_assemble_with_context(self):
        """컨텍스트 기반 조립"""
        page = assemble_page(self.modules, {"theme": "dark"})
        # 조건 없는 3개 + dark 전용 1개 = 4개
        self.assertEqual(len(page.modules), 4)
        ids = [m.module_id for m in page.modules]
        self.assertIn("m4", ids)
        self.assertNotIn("m5", ids)

    def test_assemble_priority_order(self):
        """우선순위 순 정렬"""
        page = assemble_page(self.modules, {"theme": "dark"})
        priorities = [m.priority for m in page.modules]
        self.assertEqual(priorities, sorted(priorities, reverse=True))

    def test_assemble_metadata(self):
        """메타데이터 구성"""
        page = assemble_page(self.modules, {"theme": "dark"})
        self.assertEqual(page.metadata["total_modules"], 4)
        self.assertIn("module_types", page.metadata)

    def test_assemble_layout_type(self):
        """레이아웃 유형"""
        page = assemble_page(self.modules, {}, layout_type="wide")
        self.assertEqual(page.layout_type, "wide")

    def test_assemble_empty_modules(self):
        """빈 모듈 목록"""
        page = assemble_page([], {})
        self.assertEqual(page.modules, [])
        self.assertEqual(page.metadata["total_modules"], 0)


class TestGetVariants(unittest.TestCase):
    """변형 생성 테스트"""

    def test_variants_basic(self):
        """기본 변형 생성"""
        modules = [
            ContentModule("m1", "header", "헤더", priority=10),
            ContentModule("m2", "body", "다크 본문", priority=5,
                          conditions={"theme": "dark"}),
            ContentModule("m3", "body", "라이트 본문", priority=5,
                          conditions={"theme": "light"}),
        ]
        contexts = [{"theme": "dark"}, {"theme": "light"}]
        variants = get_variants(modules, contexts)
        self.assertEqual(len(variants), 2)

    def test_variants_different_content(self):
        """변형별 다른 콘텐츠"""
        modules = [
            ContentModule("m1", "header", "공통", priority=10),
            ContentModule("m2", "body", "다크", priority=5,
                          conditions={"theme": "dark"}),
            ContentModule("m3", "body", "라이트", priority=5,
                          conditions={"theme": "light"}),
        ]
        contexts = [{"theme": "dark"}, {"theme": "light"}]
        variants = get_variants(modules, contexts)
        dark_ids = {m.module_id for m in variants[0].modules}
        light_ids = {m.module_id for m in variants[1].modules}
        self.assertIn("m2", dark_ids)
        self.assertNotIn("m3", dark_ids)
        self.assertIn("m3", light_ids)
        self.assertNotIn("m2", light_ids)

    def test_variants_empty_contexts(self):
        """빈 컨텍스트 목록"""
        modules = [ContentModule("m1", "header", "헤더")]
        variants = get_variants(modules, [])
        self.assertEqual(variants, [])

    def test_variants_layout_naming(self):
        """변형별 레이아웃 이름"""
        modules = [ContentModule("m1", "header", "헤더")]
        contexts = [{}, {}, {}]
        variants = get_variants(modules, contexts)
        self.assertEqual(variants[0].layout_type, "variant-0")
        self.assertEqual(variants[1].layout_type, "variant-1")
        self.assertEqual(variants[2].layout_type, "variant-2")


if __name__ == "__main__":
    unittest.main()
