"""의도 충돌 라우터 서비스 테스트."""

import unittest
from services.intent_conflict_router_service import (
    Intent,
    ConflictResolution,
    detect_conflicts,
    resolve_by_priority,
    propose_compromise,
    route_intent,
)


class TestIntentConflictRouterService(unittest.TestCase):
    """IntentConflictRouterService 단위 테스트."""

    def _make_intent(self, stakeholder, goal, priority=5, constraints=None):
        return Intent(
            intent_id=f"int_{stakeholder}",
            stakeholder=stakeholder,
            goal=goal,
            priority=priority,
            constraints=constraints or [],
        )

    def test_detect_conflicts_opposing_goals(self):
        """상충하는 목표가 탐지된다."""
        fast = self._make_intent("마케팅", "빠르게 출시", constraints=["즉시 배포"])
        slow = self._make_intent("법무", "신중하게 검토", constraints=["충분히 검토"])
        conflicts = detect_conflicts([fast, slow])
        self.assertTrue(len(conflicts) > 0)

    def test_detect_conflicts_no_conflict(self):
        """상충하지 않으면 빈 리스트."""
        a = self._make_intent("마케팅", "소셜미디어 캠페인")
        b = self._make_intent("개발", "서버 최적화")
        conflicts = detect_conflicts([a, b])
        self.assertEqual(len(conflicts), 0)

    def test_detect_conflicts_cost_vs_quality(self):
        """비용 절감 vs 품질 우선 충돌."""
        cost = self._make_intent("재무", "비용 절감 최우선")
        quality = self._make_intent("제품", "품질 우선 전략")
        conflicts = detect_conflicts([cost, quality])
        self.assertTrue(len(conflicts) > 0)

    def test_detect_conflicts_public_vs_private(self):
        """공개 vs 비공개 충돌."""
        pub = self._make_intent("마케팅", "콘텐츠 공개 확대")
        priv = self._make_intent("보안", "정보 기밀 유지")
        conflicts = detect_conflicts([pub, priv])
        self.assertTrue(len(conflicts) > 0)

    def test_detect_conflicts_returns_tuple(self):
        """충돌 결과는 (의도A, 의도B, 이유) 튜플."""
        expand = self._make_intent("경영", "사업 확대")
        shrink = self._make_intent("재무", "비용 축소")
        conflicts = detect_conflicts([expand, shrink])
        if conflicts:
            self.assertEqual(len(conflicts[0]), 3)

    def test_resolve_by_priority_selects_highest(self):
        """최고 우선순위 의도가 선택된다."""
        low = self._make_intent("A", "목표 A", priority=1)
        high = self._make_intent("B", "목표 B", priority=10)
        mid = self._make_intent("C", "목표 C", priority=5)

        resolution = resolve_by_priority([low, high, mid])
        self.assertEqual(resolution.resolved_goal, "목표 B")
        self.assertEqual(resolution.resolution_type, "priority_based")

    def test_resolve_by_priority_trade_offs(self):
        """양보 사항이 포함된다."""
        a = self._make_intent("A", "목표 A", priority=10)
        b = self._make_intent("B", "목표 B", priority=5)
        c = self._make_intent("C", "목표 C", priority=1)

        resolution = resolve_by_priority([a, b, c])
        self.assertEqual(len(resolution.trade_offs), 2)

    def test_resolve_by_priority_empty(self):
        """빈 목록은 '의도 없음'."""
        resolution = resolve_by_priority([])
        self.assertEqual(resolution.resolved_goal, "의도 없음")

    def test_resolve_by_priority_single(self):
        """단일 의도는 양보 없음."""
        only = self._make_intent("A", "유일한 목표", priority=5)
        resolution = resolve_by_priority([only])
        self.assertEqual(resolution.resolved_goal, "유일한 목표")
        self.assertEqual(len(resolution.trade_offs), 0)

    def test_propose_compromise(self):
        """절충안이 제안된다."""
        a = self._make_intent("마케팅", "빠른 출시", constraints=["1주 내"])
        b = self._make_intent("법무", "법적 검토", constraints=["2주 소요"])

        resolution = propose_compromise(a, b)
        self.assertEqual(resolution.resolution_type, "compromise")
        self.assertIn("균형점", resolution.resolved_goal)
        self.assertEqual(len(resolution.trade_offs), 2)

    def test_propose_compromise_includes_both_intents(self):
        """절충안에 양측 의도가 포함된다."""
        a = self._make_intent("A", "목표 A")
        b = self._make_intent("B", "목표 B")
        resolution = propose_compromise(a, b)
        self.assertEqual(len(resolution.intents), 2)

    def test_route_intent_no_conflict(self):
        """충돌 없을 때 최고 우선순위 의도로 라우팅."""
        a = self._make_intent("A", "목표 A", priority=5)
        b = self._make_intent("B", "목표 B", priority=10)

        result = route_intent([a, b])
        self.assertFalse(result["has_conflict"])
        self.assertEqual(result["resolved_goal"], "목표 B")

    def test_route_intent_with_conflict(self):
        """충돌 있을 때 해결 방법이 반환된다."""
        fast = self._make_intent("마케팅", "빠르게 출시")
        slow = self._make_intent("법무", "신중하게 검토")

        result = route_intent([fast, slow])
        self.assertTrue(result["has_conflict"])
        self.assertIn("conflict_count", result)
        self.assertIn("trade_offs", result)

    def test_route_intent_empty(self):
        """빈 의도 목록."""
        result = route_intent([])
        self.assertFalse(result["has_conflict"])
        self.assertEqual(result["resolution_type"], "no_intent")

    def test_route_intent_with_content(self):
        """콘텐츠 정보를 포함해 라우팅할 수 있다."""
        a = self._make_intent("A", "목표 A", priority=5)
        result = route_intent([a], content={"id": "c1", "type": "blog"})
        self.assertFalse(result["has_conflict"])

    def test_conflict_resolution_id_format(self):
        """ConflictResolution ID가 cr_ 접두사."""
        resolution = resolve_by_priority([self._make_intent("A", "X")])
        self.assertTrue(resolution.conflict_id.startswith("cr_"))

    def test_detect_conflicts_expand_shrink(self):
        """확대 vs 축소 충돌."""
        expand = self._make_intent("A", "시장 확장 계획")
        shrink = self._make_intent("B", "비용 최소화 계획")
        conflicts = detect_conflicts([expand, shrink])
        self.assertTrue(len(conflicts) > 0)

    def test_detect_conflicts_automation_manual(self):
        """자동화 vs 수동 충돌."""
        auto = self._make_intent("A", "업무 자동화")
        manual = self._make_intent("B", "수동 정밀 검토")
        conflicts = detect_conflicts([auto, manual])
        self.assertTrue(len(conflicts) > 0)


if __name__ == "__main__":
    unittest.main()
