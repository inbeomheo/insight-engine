"""커뮤니티 퍼널 서비스 테스트"""
import unittest

from services.community_funnel_service import (
    FunnelDesign,
    FunnelStage,
    design_funnel,
    _map_tier_to_stage,
)


class TestMapTierToStage(unittest.TestCase):
    """tier → 퍼널 단계 매핑 테스트"""

    def test_first_tier_is_awareness(self):
        tier = {'level': 0, 'name': 'free'}
        stage = _map_tier_to_stage(tier, 0, 3)
        self.assertIn("awareness", stage.name)

    def test_last_tier_is_conversion(self):
        tier = {'level': 2, 'name': 'premium'}
        stage = _map_tier_to_stage(tier, 2, 3)
        self.assertIn("conversion", stage.name)

    def test_middle_tier_mapping(self):
        tier = {'level': 1, 'name': 'basic'}
        stage = _map_tier_to_stage(tier, 1, 3)
        self.assertIsInstance(stage, FunnelStage)

    def test_single_tier_is_conversion(self):
        tier = {'level': 0, 'name': 'only'}
        stage = _map_tier_to_stage(tier, 0, 1)
        self.assertIn("conversion", stage.name)

    def test_custom_content_type_used(self):
        tier = {'level': 1, 'name': 'custom', 'content_type': '맞춤 콘텐츠'}
        stage = _map_tier_to_stage(tier, 1, 3)
        self.assertEqual(stage.content_type, '맞춤 콘텐츠')

    def test_custom_access_used(self):
        tier = {'level': 0, 'name': 'test', 'access': 'restricted'}
        stage = _map_tier_to_stage(tier, 0, 2)
        self.assertEqual(stage.access, 'restricted')


class TestDesignFunnel(unittest.TestCase):
    """퍼널 설계 통합 테스트"""

    def test_empty_tiers_returns_default(self):
        """tier 없으면 기본 4단계 반환"""
        result = design_funnel([])
        self.assertIsInstance(result, FunnelDesign)
        self.assertEqual(result.total_tiers, 4)
        self.assertEqual(len(result.stages), 4)

    def test_default_stage_names(self):
        result = design_funnel([])
        names = [s.name for s in result.stages]
        self.assertIn("awareness", names)
        self.assertIn("interest", names)
        self.assertIn("consideration", names)
        self.assertIn("conversion", names)

    def test_custom_tiers(self):
        tiers = [
            {'level': 0, 'name': 'free'},
            {'level': 1, 'name': 'basic'},
            {'level': 2, 'name': 'pro'},
        ]
        result = design_funnel(tiers)
        self.assertEqual(result.total_tiers, 3)
        self.assertEqual(len(result.stages), 3)

    def test_tiers_sorted_by_level(self):
        """입력 순서와 관계없이 level로 정렬"""
        tiers = [
            {'level': 2, 'name': 'pro'},
            {'level': 0, 'name': 'free'},
            {'level': 1, 'name': 'basic'},
        ]
        result = design_funnel(tiers)
        levels = [s.tier_level for s in result.stages]
        self.assertEqual(levels, [0, 1, 2])

    def test_conversion_targets_generated(self):
        tiers = [
            {'level': 0, 'name': 'free'},
            {'level': 1, 'name': 'basic'},
            {'level': 2, 'name': 'pro'},
        ]
        result = design_funnel(tiers)
        self.assertGreater(len(result.conversion_targets), 0)
        # n-1 개의 전환 목표
        self.assertEqual(len(result.conversion_targets), 2)

    def test_conversion_targets_decreasing(self):
        """뒤 단계로 갈수록 전환 목표 감소"""
        tiers = [
            {'level': 0, 'name': 'a'},
            {'level': 1, 'name': 'b'},
            {'level': 2, 'name': 'c'},
            {'level': 3, 'name': 'd'},
        ]
        result = design_funnel(tiers)
        rates = list(result.conversion_targets.values())
        for i in range(len(rates) - 1):
            self.assertGreaterEqual(rates[i], rates[i + 1])

    def test_single_tier(self):
        result = design_funnel([{'level': 0, 'name': 'solo'}])
        self.assertEqual(result.total_tiers, 1)
        self.assertEqual(len(result.stages), 1)
        # 전환 목표 없음 (다음 단계 없으므로)
        self.assertEqual(len(result.conversion_targets), 0)

    def test_stage_has_required_fields(self):
        result = design_funnel([{'level': 0, 'name': 'test'}, {'level': 1, 'name': 'paid'}])
        for stage in result.stages:
            self.assertTrue(stage.name)
            self.assertTrue(stage.content_type)
            self.assertTrue(stage.access)
            self.assertTrue(stage.conversion_action)

    def test_default_funnel_access_types(self):
        """기본 퍼널의 접근 권한 패턴 확인"""
        result = design_funnel([])
        accesses = [s.access for s in result.stages]
        self.assertIn("free", accesses)
        self.assertIn("paid", accesses)

    def test_many_tiers(self):
        """많은 tier도 처리 가능"""
        tiers = [{'level': i, 'name': f'tier_{i}'} for i in range(10)]
        result = design_funnel(tiers)
        self.assertEqual(result.total_tiers, 10)
        self.assertEqual(len(result.stages), 10)
        self.assertEqual(len(result.conversion_targets), 9)


if __name__ == '__main__':
    unittest.main()
