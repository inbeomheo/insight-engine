"""크리에이터 매처 서비스 테스트 — 15개+ 테스트 케이스."""

import unittest
from services.creator_matcher_service import (
    MatchResult,
    match_creators,
    _normalize_topic,
    _normalize_topics,
    _compute_direct_overlap,
    _compute_indirect_similarity,
    _compute_audience_overlap,
    _generate_collaboration_ideas,
    _compute_match_score,
)


class TestNormalizeTopic(unittest.TestCase):
    """토픽 정규화 테스트"""

    def test_known_alias(self):
        """알려진 별칭이 표준 키로 변환"""
        self.assertEqual(_normalize_topic("technology"), "tech")
        self.assertEqual(_normalize_topic("artificial intelligence"), "ai")
        self.assertEqual(_normalize_topic("스타트업"), "business")

    def test_unknown_passthrough(self):
        """알 수 없는 토픽은 소문자로 반환"""
        self.assertEqual(_normalize_topic("Astronomy"), "astronomy")

    def test_korean_alias(self):
        """한국어 별칭 정규화"""
        self.assertEqual(_normalize_topic("개발"), "tech")
        self.assertEqual(_normalize_topic("디자인"), "design")
        self.assertEqual(_normalize_topic("재테크"), "finance")


class TestNormalizeTopics(unittest.TestCase):
    """토픽 리스트 정규화 테스트"""

    def test_deduplication(self):
        """중복 제거"""
        result = _normalize_topics(["tech", "technology", "programming"])
        self.assertEqual(result, ["tech"])

    def test_empty_and_invalid_skipped(self):
        """빈 문자열과 비문자열 건너뜀"""
        result = _normalize_topics(["tech", "", None, 42, "ai"])
        self.assertEqual(result, ["tech", "ai"])

    def test_order_preserved(self):
        """입력 순서 유지 (중복 제거 후)"""
        result = _normalize_topics(["ai", "tech", "design"])
        self.assertEqual(result, ["ai", "tech", "design"])


class TestComputeDirectOverlap(unittest.TestCase):
    """직접 토픽 오버랩 테스트"""

    def test_full_overlap(self):
        """완전 일치 시 1.0"""
        score, shared = _compute_direct_overlap(["tech", "ai"], ["tech", "ai"])
        self.assertEqual(score, 1.0)
        self.assertEqual(set(shared), {"tech", "ai"})

    def test_partial_overlap(self):
        """부분 일치"""
        score, shared = _compute_direct_overlap(["tech", "ai"], ["tech", "design"])
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)
        self.assertEqual(shared, ["tech"])

    def test_no_overlap(self):
        """겹침 없음"""
        score, shared = _compute_direct_overlap(["tech"], ["design"])
        self.assertEqual(score, 0.0)
        self.assertEqual(shared, [])

    def test_both_empty(self):
        """둘 다 빈 리스트"""
        score, shared = _compute_direct_overlap([], [])
        self.assertEqual(score, 0.0)
        self.assertEqual(shared, [])


class TestComputeIndirectSimilarity(unittest.TestCase):
    """간접 토픽 유사도 테스트"""

    def test_related_topics(self):
        """관련 토픽 간 양수 유사도"""
        score = _compute_indirect_similarity(["tech"], ["ai"])
        self.assertGreater(score, 0.0)

    def test_unrelated_topics(self):
        """무관한 토픽 간 0 유사도"""
        score = _compute_indirect_similarity(["gaming"], ["finance"])
        self.assertEqual(score, 0.0)

    def test_empty_returns_zero(self):
        """빈 리스트는 0"""
        self.assertEqual(_compute_indirect_similarity([], ["tech"]), 0.0)
        self.assertEqual(_compute_indirect_similarity(["tech"], []), 0.0)

    def test_max_capped_at_half(self):
        """간접 유사도는 0.5 이하"""
        # 여러 관련 토픽 조합
        score = _compute_indirect_similarity(
            ["tech", "ai", "education"],
            ["business", "marketing", "design"],
        )
        self.assertLessEqual(score, 0.5)


class TestComputeAudienceOverlap(unittest.TestCase):
    """오디언스 오버랩 테스트"""

    def test_similar_size(self):
        """비슷한 규모 → 높은 오버랩"""
        overlap = _compute_audience_overlap(10000, 12000)
        self.assertGreaterEqual(overlap, 0.7)

    def test_large_difference(self):
        """큰 차이 → 낮은 오버랩"""
        overlap = _compute_audience_overlap(1000, 1_000_000)
        self.assertLessEqual(overlap, 0.3)

    def test_zero_audience(self):
        """0인 오디언스 → 기본값 0.2"""
        self.assertEqual(_compute_audience_overlap(0, 10000), 0.2)
        self.assertEqual(_compute_audience_overlap(10000, 0), 0.2)

    def test_equal_size(self):
        """동일 규모 → 최고 오버랩"""
        overlap = _compute_audience_overlap(50000, 50000)
        self.assertEqual(overlap, 0.9)


class TestGenerateCollaborationIdeas(unittest.TestCase):
    """협업 아이디어 생성 테스트"""

    def test_shared_topic_ideas(self):
        """공통 토픽 기반 아이디어 생성"""
        ideas = _generate_collaboration_ideas(["tech"], ["tech"], ["tech"])
        self.assertGreater(len(ideas), 0)

    def test_fallback_when_no_shared(self):
        """공통 토픽 없을 때 범용 아이디어 반환"""
        ideas = _generate_collaboration_ideas([], ["unknown_x"], ["unknown_y"])
        self.assertGreater(len(ideas), 0)

    def test_max_5_ideas(self):
        """최대 5개 아이디어"""
        ideas = _generate_collaboration_ideas(
            ["tech", "ai", "marketing"],
            ["tech", "ai", "marketing", "design"],
            ["tech", "ai", "marketing", "business"],
        )
        self.assertLessEqual(len(ideas), 5)


class TestComputeMatchScore(unittest.TestCase):
    """종합 매칭 점수 테스트"""

    def test_perfect_match(self):
        """완벽 매칭 → 100점"""
        score = _compute_match_score(1.0, 1.0, 1.0)
        self.assertEqual(score, 100.0)

    def test_zero_match(self):
        """매칭 없음 → 0점"""
        score = _compute_match_score(0.0, 0.0, 0.0)
        self.assertEqual(score, 0.0)

    def test_range_0_to_100(self):
        """점수가 0~100 범위"""
        score = _compute_match_score(0.5, 0.3, 0.7)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_topic_weight_dominant(self):
        """직접 토픽 오버랩이 50% 가중치"""
        high_topic = _compute_match_score(1.0, 0.0, 0.0)
        high_audience = _compute_match_score(0.0, 0.0, 1.0)
        self.assertGreater(high_topic, high_audience)


class TestMatchCreators(unittest.TestCase):
    """match_creators 통합 테스트"""

    def test_basic_matching(self):
        """기본 매칭 시나리오"""
        channel = {"name": "테크채널", "topics": ["tech", "ai"], "audience_size": 50000}
        candidates = [
            {"name": "크리에이터A", "topics": ["tech", "design"], "audience_size": 40000},
            {"name": "크리에이터B", "topics": ["marketing", "business"], "audience_size": 60000},
        ]
        results = match_creators(channel, candidates)

        self.assertEqual(len(results), 2)
        # 토픽 오버랩이 있는 A가 더 높은 점수
        self.assertGreater(results[0].match_score, results[1].match_score)
        self.assertEqual(results[0].creator_name, "크리에이터A")

    def test_sorted_by_score_desc(self):
        """결과가 점수 내림차순 정렬"""
        channel = {"name": "채널", "topics": ["tech"], "audience_size": 10000}
        candidates = [
            {"name": "낮은", "topics": ["design"], "audience_size": 100},
            {"name": "높은", "topics": ["tech"], "audience_size": 10000},
            {"name": "중간", "topics": ["ai"], "audience_size": 5000},
        ]
        results = match_creators(channel, candidates)
        scores = [r.match_score for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_score_range_0_to_100(self):
        """모든 점수가 0~100 범위"""
        channel = {"name": "채널", "topics": ["tech"], "audience_size": 10000}
        candidates = [
            {"name": "A", "topics": ["tech"], "audience_size": 10000},
            {"name": "B", "topics": [], "audience_size": 0},
        ]
        results = match_creators(channel, candidates)
        for r in results:
            self.assertGreaterEqual(r.match_score, 0.0)
            self.assertLessEqual(r.match_score, 100.0)

    def test_shared_topics_populated(self):
        """공통 토픽이 올바르게 채워지는지 확인"""
        channel = {"name": "채널", "topics": ["tech", "ai"], "audience_size": 10000}
        candidates = [{"name": "A", "topics": ["tech", "design"], "audience_size": 10000}]
        results = match_creators(channel, candidates)
        self.assertIn("tech", results[0].shared_topics)

    def test_collaboration_ideas_populated(self):
        """협업 아이디어가 생성되는지 확인"""
        channel = {"name": "채널", "topics": ["tech"], "audience_size": 10000}
        candidates = [{"name": "A", "topics": ["tech"], "audience_size": 10000}]
        results = match_creators(channel, candidates)
        self.assertGreater(len(results[0].collaboration_ideas), 0)

    def test_audience_overlap_field(self):
        """audience_overlap 필드가 0~1 범위"""
        channel = {"name": "채널", "topics": ["tech"], "audience_size": 10000}
        candidates = [{"name": "A", "topics": ["tech"], "audience_size": 10000}]
        results = match_creators(channel, candidates)
        self.assertGreaterEqual(results[0].audience_overlap, 0.0)
        self.assertLessEqual(results[0].audience_overlap, 1.0)

    def test_none_channel_raises(self):
        """channel_profile이 None이면 ValueError"""
        with self.assertRaises(ValueError):
            match_creators(None, [])

    def test_none_candidates_raises(self):
        """candidates가 None이면 ValueError"""
        with self.assertRaises(ValueError):
            match_creators({"name": "채널", "topics": []}, None)

    def test_no_name_raises(self):
        """channel_profile에 name이 없으면 ValueError"""
        with self.assertRaises(ValueError):
            match_creators({"topics": ["tech"]}, [])

    def test_candidate_without_name_skipped(self):
        """이름 없는 후보는 건너뜀"""
        channel = {"name": "채널", "topics": ["tech"], "audience_size": 10000}
        candidates = [
            {"topics": ["tech"], "audience_size": 10000},  # 이름 없음
            {"name": "유효", "topics": ["tech"], "audience_size": 10000},
        ]
        results = match_creators(channel, candidates)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].creator_name, "유효")

    def test_empty_candidates(self):
        """빈 후보 리스트 → 빈 결과"""
        channel = {"name": "채널", "topics": ["tech"], "audience_size": 10000}
        results = match_creators(channel, [])
        self.assertEqual(results, [])

    def test_invalid_candidate_type_skipped(self):
        """dict가 아닌 후보는 건너뜀"""
        channel = {"name": "채널", "topics": ["tech"], "audience_size": 10000}
        candidates = ["not_a_dict", 123, {"name": "유효", "topics": ["tech"]}]
        results = match_creators(channel, candidates)
        self.assertEqual(len(results), 1)

    def test_korean_topics_normalized(self):
        """한국어 토픽이 정규화되어 매칭"""
        channel = {"name": "채널", "topics": ["인공지능", "마케팅"], "audience_size": 10000}
        candidates = [{"name": "A", "topics": ["ai", "marketing"], "audience_size": 10000}]
        results = match_creators(channel, candidates)
        self.assertGreater(results[0].match_score, 50)  # 높은 매칭

    def test_non_numeric_audience_handled(self):
        """audience_size가 숫자가 아닌 경우 안전 처리"""
        channel = {"name": "채널", "topics": ["tech"], "audience_size": "invalid"}
        candidates = [{"name": "A", "topics": ["tech"], "audience_size": "also_invalid"}]
        results = match_creators(channel, candidates)
        self.assertEqual(len(results), 1)
        # 에러 없이 기본값으로 처리
        self.assertGreaterEqual(results[0].match_score, 0.0)

    def test_dataclass_fields(self):
        """MatchResult 필드 타입 확인"""
        channel = {"name": "채널", "topics": ["tech"], "audience_size": 10000}
        candidates = [{"name": "A", "topics": ["tech"], "audience_size": 10000}]
        results = match_creators(channel, candidates)
        r = results[0]
        self.assertIsInstance(r.creator_name, str)
        self.assertIsInstance(r.match_score, float)
        self.assertIsInstance(r.shared_topics, list)
        self.assertIsInstance(r.audience_overlap, float)
        self.assertIsInstance(r.collaboration_ideas, list)


if __name__ == "__main__":
    unittest.main()
