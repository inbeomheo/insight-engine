"""딥리서치 에이전트 서비스 테스트."""

import unittest
from services.deep_research_agent_service import (
    ResearchQuery,
    ResearchFinding,
    decompose_query,
    evaluate_finding,
    synthesize_findings,
    rank_findings,
)


class TestDecomposeQuery(unittest.TestCase):
    """쿼리 분해 테스트."""

    def test_decompose_basic(self):
        """기본 토픽 분해."""
        query = decompose_query("인공지능 기술 동향")
        self.assertTrue(query.query_id)
        self.assertEqual(query.topic, "인공지능 기술 동향")
        self.assertGreaterEqual(len(query.sub_questions), 3)
        self.assertLessEqual(len(query.sub_questions), 5)

    def test_decompose_contains_topic(self):
        """하위 질문에 토픽 포함."""
        query = decompose_query("블록체인")
        for q in query.sub_questions:
            self.assertIn("블록체인", q)

    def test_decompose_depth_default(self):
        """기본 깊이 medium."""
        query = decompose_query("테스트 토픽")
        self.assertEqual(query.depth, "medium")

    def test_decompose_question_count(self):
        """medium 깊이 → 4개 질문."""
        query = decompose_query("데이터 분석")
        self.assertEqual(len(query.sub_questions), 4)

    def test_decompose_unique_questions(self):
        """하위 질문 중복 없음."""
        query = decompose_query("머신러닝")
        self.assertEqual(len(query.sub_questions), len(set(query.sub_questions)))


class TestEvaluateFinding(unittest.TestCase):
    """리서치 결과 평가 테스트."""

    def test_evaluate_high_relevance(self):
        """키워드 매칭 높을 때 높은 관련성."""
        finding = evaluate_finding(
            "인공지능 기술은 빠르게 발전하고 있다",
            "인공지능 기술"
        )
        self.assertGreater(finding.relevance_score, 0.5)

    def test_evaluate_low_relevance(self):
        """키워드 매칭 없을 때 낮은 관련성."""
        finding = evaluate_finding(
            "오늘 날씨가 좋다",
            "인공지능 기술 동향"
        )
        self.assertLessEqual(finding.relevance_score, 0.5)

    def test_evaluate_credibility_high(self):
        """긴 콘텐츠 → 높은 신뢰도."""
        long_content = "상세한 분석 내용입니다. " * 30  # 200자 이상
        finding = evaluate_finding(long_content, "분석")
        self.assertEqual(finding.credibility, "high")

    def test_evaluate_credibility_medium(self):
        """중간 길이 → 중간 신뢰도."""
        content = "중간 정도의 내용입니다. " * 5  # 50~200자
        finding = evaluate_finding(content, "내용")
        self.assertEqual(finding.credibility, "medium")

    def test_evaluate_credibility_low(self):
        """짧은 콘텐츠 → 낮은 신뢰도."""
        finding = evaluate_finding("짧음", "토픽")
        self.assertEqual(finding.credibility, "low")

    def test_evaluate_empty_topic(self):
        """빈 토픽 → 기본 관련성 0.5."""
        finding = evaluate_finding("콘텐츠", "")
        self.assertEqual(finding.relevance_score, 0.5)

    def test_evaluate_has_finding_id(self):
        """finding_id 생성 확인."""
        finding = evaluate_finding("콘텐츠", "토픽")
        self.assertTrue(finding.finding_id)

    def test_evaluate_relevance_bounded(self):
        """관련성 점수 0~1 범위."""
        finding = evaluate_finding("모든 키워드를 포함하는 텍스트", "모든 키워드")
        self.assertGreaterEqual(finding.relevance_score, 0.0)
        self.assertLessEqual(finding.relevance_score, 1.0)


class TestSynthesizeFindings(unittest.TestCase):
    """결과 종합 테스트."""

    def test_synthesize_empty(self):
        """빈 결과 → 빈 문자열."""
        result = synthesize_findings([])
        self.assertEqual(result, "")

    def test_synthesize_single(self):
        """단일 결과 종합."""
        finding = ResearchFinding("f1", "q1", "논문A", "AI 연구 결과", 0.9, "high")
        result = synthesize_findings([finding])
        self.assertIn("논문A", result)
        self.assertIn("AI 연구 결과", result)

    def test_synthesize_ordered_by_relevance(self):
        """관련성 높은 순 정렬."""
        findings = [
            ResearchFinding("f1", "q1", "소스A", "낮은 관련", 0.3, "low"),
            ResearchFinding("f2", "q1", "소스B", "높은 관련", 0.9, "high"),
        ]
        result = synthesize_findings(findings)
        # 높은 관련성이 먼저 나와야 함
        pos_high = result.index("높은 관련")
        pos_low = result.index("낮은 관련")
        self.assertLess(pos_high, pos_low)

    def test_synthesize_includes_metadata(self):
        """메타데이터 (관련성, 신뢰도) 포함."""
        finding = ResearchFinding("f1", "q1", "출처", "내용", 0.8, "high")
        result = synthesize_findings([finding])
        self.assertIn("0.8", result)
        self.assertIn("high", result)


class TestRankFindings(unittest.TestCase):
    """결과 랭킹 테스트."""

    def test_rank_by_composite(self):
        """복합 점수(관련성 * 신뢰도 가중치) 내림차순."""
        findings = [
            ResearchFinding("f1", "q1", "A", "내용A", 0.5, "high"),   # 0.5 * 1.0 = 0.5
            ResearchFinding("f2", "q1", "B", "내용B", 0.9, "low"),    # 0.9 * 0.4 = 0.36
            ResearchFinding("f3", "q1", "C", "내용C", 0.8, "medium"), # 0.8 * 0.7 = 0.56
        ]
        ranked = rank_findings(findings)
        self.assertEqual(ranked[0].finding_id, "f3")  # 0.56
        self.assertEqual(ranked[1].finding_id, "f1")  # 0.5
        self.assertEqual(ranked[2].finding_id, "f2")  # 0.36

    def test_rank_empty(self):
        """빈 목록."""
        result = rank_findings([])
        self.assertEqual(result, [])

    def test_rank_single(self):
        """단일 결과."""
        finding = ResearchFinding("f1", "q1", "A", "내용", 0.7, "high")
        ranked = rank_findings([finding])
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0].finding_id, "f1")

    def test_rank_same_relevance_different_credibility(self):
        """같은 관련성, 다른 신뢰도 → 높은 신뢰도 우선."""
        findings = [
            ResearchFinding("f1", "q1", "A", "내용A", 0.8, "low"),    # 0.32
            ResearchFinding("f2", "q1", "B", "내용B", 0.8, "high"),   # 0.8
        ]
        ranked = rank_findings(findings)
        self.assertEqual(ranked[0].finding_id, "f2")


if __name__ == "__main__":
    unittest.main()
