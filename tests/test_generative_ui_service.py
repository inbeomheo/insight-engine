"""제너레이티브 UI 서비스 테스트"""

import unittest
from services.generative_ui_service import (
    UIComponent, UILayout,
    generate_layout, add_component, reorder_components, export_layout_spec,
    VALID_COMPONENT_TYPES,
)


class TestGenerateLayout(unittest.TestCase):
    """generate_layout 테스트"""

    def test_blog_layout_has_2_cols(self):
        """blog 타입은 2열 그리드"""
        layout = generate_layout("테스트 콘텐츠", "blog")
        self.assertEqual(layout.grid_cols, 2)

    def test_dashboard_layout_has_3_cols(self):
        """dashboard 타입은 3열 그리드"""
        layout = generate_layout("대시보드 내용", "dashboard")
        self.assertEqual(layout.grid_cols, 3)

    def test_landing_layout_has_1_col(self):
        """landing 타입은 1열 그리드"""
        layout = generate_layout("랜딩 페이지", "landing")
        self.assertEqual(layout.grid_cols, 1)

    def test_unknown_type_defaults_to_1_col(self):
        """알 수 없는 타입은 1열 기본"""
        layout = generate_layout("기타", "unknown_type")
        self.assertEqual(layout.grid_cols, 1)

    def test_layout_has_components(self):
        """생성된 레이아웃에 컴포넌트가 있어야 함"""
        layout = generate_layout("블로그 콘텐츠", "blog")
        self.assertGreater(len(layout.components), 0)

    def test_component_positions_calculated(self):
        """컴포넌트 위치가 올바르게 계산됨"""
        layout = generate_layout("테스트", "blog")  # 2열
        for comp in layout.components:
            self.assertIn("row", comp.position)
            self.assertIn("col", comp.position)

    def test_layout_id_generated(self):
        """레이아웃 ID가 생성됨"""
        layout = generate_layout("테스트", "blog")
        self.assertTrue(layout.layout_id.startswith("layout_"))

    def test_layout_title_contains_type(self):
        """레이아웃 제목에 콘텐츠 타입 포함"""
        layout = generate_layout("테스트", "blog")
        self.assertIn("blog", layout.title)


class TestAddComponent(unittest.TestCase):
    """add_component 테스트"""

    def test_add_component_increases_count(self):
        """컴포넌트 추가 시 개수 증가"""
        layout = generate_layout("테스트", "blog")
        original_count = len(layout.components)
        updated = add_component(layout, "card", "새 카드")
        self.assertEqual(len(updated.components), original_count + 1)

    def test_add_component_preserves_existing(self):
        """기존 컴포넌트가 유지됨"""
        layout = generate_layout("테스트", "blog")
        first_id = layout.components[0].component_id
        updated = add_component(layout, "text", "추가 텍스트")
        self.assertEqual(updated.components[0].component_id, first_id)

    def test_invalid_component_type_raises(self):
        """유효하지 않은 타입이면 ValueError"""
        layout = generate_layout("테스트", "blog")
        with self.assertRaises(ValueError):
            add_component(layout, "invalid_type", "내용")

    def test_add_with_custom_style(self):
        """커스텀 스타일 적용"""
        layout = generate_layout("테스트", "landing")
        style = {"color": "red", "fontSize": "16px"}
        updated = add_component(layout, "cta", "버튼", style=style)
        last_comp = updated.components[-1]
        self.assertEqual(last_comp.style["color"], "red")


class TestReorderComponents(unittest.TestCase):
    """reorder_components 테스트"""

    def test_reorder_changes_positions(self):
        """재정렬 후 위치가 업데이트됨"""
        layout = generate_layout("테스트", "blog")
        ids = [c.component_id for c in layout.components]
        reversed_ids = list(reversed(ids))

        updated = reorder_components(layout, reversed_ids)
        self.assertEqual(updated.components[0].component_id, reversed_ids[0])

    def test_reorder_invalid_id_raises(self):
        """존재하지 않는 ID로 재정렬하면 ValueError"""
        layout = generate_layout("테스트", "blog")
        with self.assertRaises(ValueError):
            reorder_components(layout, ["nonexistent_id"])

    def test_partial_reorder_keeps_remaining(self):
        """일부 ID만 재정렬하면 나머지는 뒤에 유지"""
        layout = generate_layout("테스트", "blog")
        if len(layout.components) >= 2:
            first_id = layout.components[0].component_id
            updated = reorder_components(layout, [first_id])
            self.assertEqual(len(updated.components), len(layout.components))


class TestExportLayoutSpec(unittest.TestCase):
    """export_layout_spec 테스트"""

    def test_export_returns_dict(self):
        """dict 반환"""
        layout = generate_layout("테스트", "blog")
        spec = export_layout_spec(layout)
        self.assertIsInstance(spec, dict)

    def test_export_has_required_fields(self):
        """필수 필드 포함"""
        layout = generate_layout("테스트", "dashboard")
        spec = export_layout_spec(layout)
        self.assertIn("layout_id", spec)
        self.assertIn("title", spec)
        self.assertIn("grid_cols", spec)
        self.assertIn("components", spec)
        self.assertIn("component_count", spec)

    def test_export_component_count_matches(self):
        """컴포넌트 수가 일치"""
        layout = generate_layout("테스트", "blog")
        spec = export_layout_spec(layout)
        self.assertEqual(spec["component_count"], len(layout.components))

    def test_export_components_are_dicts(self):
        """컴포넌트가 dict로 직렬화됨"""
        layout = generate_layout("테스트", "blog")
        spec = export_layout_spec(layout)
        for comp in spec["components"]:
            self.assertIsInstance(comp, dict)
            self.assertIn("component_id", comp)


if __name__ == "__main__":
    unittest.main()
