"""정책 기반 콘텐츠 라우팅 서비스 테스트."""

import unittest
from services.policy_routing_service import (
    RoutingPolicy,
    RoutingDecision,
    create_policy,
    evaluate_content,
    match_condition,
    get_default_route,
)


class TestPolicyRoutingService(unittest.TestCase):
    """PolicyRoutingService 단위 테스트."""

    def test_create_policy_returns_routing_policy(self):
        """정책 생성 시 RoutingPolicy 인스턴스를 반환한다."""
        policy = create_policy(
            name="긴 콘텐츠",
            conditions=[{"field": "word_count", "operator": "gt", "value": 1000}],
            target="long_content_pipeline",
            priority=10,
        )
        self.assertIsInstance(policy, RoutingPolicy)
        self.assertEqual(policy.name, "긴 콘텐츠")
        self.assertEqual(policy.target_pipeline, "long_content_pipeline")
        self.assertEqual(policy.priority, 10)
        self.assertTrue(policy.policy_id.startswith("pol_"))

    def test_match_condition_eq(self):
        """eq 연산자 — 값이 동일하면 True."""
        content = {"type": "blog"}
        self.assertTrue(match_condition(content, {"field": "type", "operator": "eq", "value": "blog"}))
        self.assertFalse(match_condition(content, {"field": "type", "operator": "eq", "value": "video"}))

    def test_match_condition_contains(self):
        """contains 연산자 — 값이 포함되면 True."""
        content = {"title": "Python 프로그래밍 입문"}
        self.assertTrue(match_condition(content, {"field": "title", "operator": "contains", "value": "Python"}))
        self.assertFalse(match_condition(content, {"field": "title", "operator": "contains", "value": "Java"}))

    def test_match_condition_gt_lt(self):
        """gt/lt 연산자 — 숫자 비교."""
        content = {"word_count": 1500}
        self.assertTrue(match_condition(content, {"field": "word_count", "operator": "gt", "value": 1000}))
        self.assertFalse(match_condition(content, {"field": "word_count", "operator": "lt", "value": 1000}))

    def test_match_condition_in_operator(self):
        """in 연산자 — 값이 목록에 포함되면 True."""
        content = {"category": "tech"}
        cond = {"field": "category", "operator": "in", "value": ["tech", "science"]}
        self.assertTrue(match_condition(content, cond))

        content2 = {"category": "sports"}
        self.assertFalse(match_condition(content2, cond))

    def test_match_condition_missing_field(self):
        """필드가 없으면 False."""
        content = {"title": "test"}
        self.assertFalse(match_condition(content, {"field": "missing", "operator": "eq", "value": "x"}))

    def test_match_condition_invalid_operator(self):
        """지원하지 않는 연산자면 False."""
        content = {"value": 10}
        self.assertFalse(match_condition(content, {"field": "value", "operator": "regex", "value": ".*"}))

    def test_match_condition_gt_non_numeric(self):
        """gt에 숫자가 아닌 값이면 False."""
        content = {"value": "abc"}
        self.assertFalse(match_condition(content, {"field": "value", "operator": "gt", "value": 10}))

    def test_evaluate_content_matches_highest_priority(self):
        """우선순위 높은 정책이 선택된다."""
        p1 = create_policy("저우선", [{"field": "type", "operator": "eq", "value": "blog"}], "pipe_a", 1)
        p2 = create_policy("고우선", [{"field": "type", "operator": "eq", "value": "blog"}], "pipe_b", 10)
        content = {"id": "c1", "type": "blog"}

        decision = evaluate_content(content, [p1, p2])
        self.assertEqual(decision.target_pipeline, "pipe_b")
        self.assertEqual(decision.matched_policy, "고우선")

    def test_evaluate_content_multiple_conditions(self):
        """모든 조건을 만족해야 매칭된다."""
        policy = create_policy(
            "복합 조건",
            [
                {"field": "type", "operator": "eq", "value": "blog"},
                {"field": "word_count", "operator": "gt", "value": 500},
            ],
            "complex_pipeline",
            5,
        )
        content_match = {"id": "c1", "type": "blog", "word_count": 1000}
        content_no_match = {"id": "c2", "type": "blog", "word_count": 100}

        self.assertEqual(evaluate_content(content_match, [policy]).target_pipeline, "complex_pipeline")
        self.assertEqual(evaluate_content(content_no_match, [policy]).matched_policy, "default")

    def test_evaluate_content_no_match_uses_default(self):
        """매칭 정책이 없으면 기본 라우트를 사용한다."""
        policy = create_policy("비디오만", [{"field": "type", "operator": "eq", "value": "video"}], "vid_pipe", 1)
        content = {"id": "c1", "type": "blog"}

        decision = evaluate_content(content, [policy])
        self.assertEqual(decision.matched_policy, "default")

    def test_get_default_route_by_type(self):
        """콘텐츠 유형별 기본 라우트를 반환한다."""
        self.assertEqual(get_default_route({"type": "blog"}), "standard_blog_pipeline")
        self.assertEqual(get_default_route({"type": "video"}), "video_processing_pipeline")
        self.assertEqual(get_default_route({"type": "social"}), "social_media_pipeline")

    def test_get_default_route_unknown_type(self):
        """알 수 없는 유형은 general_pipeline."""
        self.assertEqual(get_default_route({"type": "unknown"}), "general_pipeline")
        self.assertEqual(get_default_route({}), "general_pipeline")

    def test_evaluate_content_returns_routing_decision(self):
        """평가 결과는 RoutingDecision 인스턴스다."""
        decision = evaluate_content({"id": "c1"}, [])
        self.assertIsInstance(decision, RoutingDecision)
        self.assertEqual(decision.content_id, "c1")

    def test_match_condition_in_with_non_list(self):
        """in 연산자에 리스트가 아닌 값이면 False."""
        content = {"x": "a"}
        self.assertFalse(match_condition(content, {"field": "x", "operator": "in", "value": "abc"}))


if __name__ == "__main__":
    unittest.main()
