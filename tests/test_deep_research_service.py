"""
멀티소스 리서치 서비스 테스트
"""
import unittest

from services.deep_research_service import (
    AVAILABLE_SOURCES,
    Finding,
    ResearchReport,
    multi_source_research,
    _calculate_confidence,
    _calculate_relevance,
    _create_finding,
    _extract_domain,
    _generate_hash,
)


class TestMultiSourceResearch(unittest.TestCase):
    """multi_source_research 함수 테스트."""

    def test_default_sources_returns_all(self):
        """소스 미지정 시 전체 소스 사용."""
        report = multi_source_research("인공지능")
        self.assertEqual(sorted(report.sources_used), sorted(AVAILABLE_SOURCES))
        self.assertEqual(len(report.findings), len(AVAILABLE_SOURCES))

    def test_specific_sources(self):
        """특정 소스만 지정했을 때 해당 소스만 사용."""
        sources = ["academic", "news"]
        report = multi_source_research("블록체인", sources=sources)
        self.assertEqual(sorted(report.sources_used), sorted(sources))
        self.assertEqual(len(report.findings), 2)
        for f in report.findings:
            self.assertIn(f.source, sources)

    def test_single_source(self):
        """단일 소스 지정."""
        report = multi_source_research("양자컴퓨팅", sources=["patent"])
        self.assertEqual(report.sources_used, ["patent"])
        self.assertEqual(len(report.findings), 1)
        self.assertEqual(report.findings[0].source, "patent")

    def test_empty_query_raises(self):
        """빈 쿼리 시 ValueError."""
        with self.assertRaises(ValueError):
            multi_source_research("")
        with self.assertRaises(ValueError):
            multi_source_research("   ")

    def test_invalid_source_raises(self):
        """유효하지 않은 소스 시 ValueError."""
        with self.assertRaises(ValueError):
            multi_source_research("테스트", sources=["invalid_source"])

    def test_empty_sources_list_uses_all(self):
        """빈 소스 리스트 시 전체 소스 사용."""
        report = multi_source_research("테스트", sources=[])
        self.assertEqual(sorted(report.sources_used), sorted(AVAILABLE_SOURCES))

    def test_report_query_stored(self):
        """보고서에 쿼리가 저장됨."""
        report = multi_source_research("  머신러닝 트렌드  ")
        self.assertEqual(report.query, "머신러닝 트렌드")

    def test_findings_sorted_by_relevance(self):
        """Finding이 관련도 내림차순 정렬."""
        report = multi_source_research("딥러닝")
        scores = [f.relevance_score for f in report.findings]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_confidence_range(self):
        """confidence 값이 0~1.0 범위."""
        report = multi_source_research("자연어처리")
        self.assertGreaterEqual(report.confidence, 0.0)
        self.assertLessEqual(report.confidence, 1.0)

    def test_summary_contains_query(self):
        """요약에 쿼리 문자열 포함."""
        report = multi_source_research("로보틱스")
        self.assertIn("로보틱스", report.summary)

    def test_summary_contains_count(self):
        """요약에 결과 수 포함."""
        report = multi_source_research("IoT", sources=["news", "blog"])
        self.assertIn("2건", report.summary)

    def test_finding_has_citation(self):
        """Finding에 인용 정보 포함."""
        report = multi_source_research("클라우드", sources=["academic"])
        finding = report.findings[0]
        self.assertIn("[학술]", finding.citation)
        self.assertIn("클라우드", finding.citation)

    def test_finding_title_contains_query(self):
        """Finding 제목에 쿼리 포함."""
        report = multi_source_research("데이터분석")
        for f in report.findings:
            self.assertIn("데이터분석", f.title)

    def test_report_is_dataclass(self):
        """반환 타입이 ResearchReport."""
        report = multi_source_research("테스트")
        self.assertIsInstance(report, ResearchReport)
        for f in report.findings:
            self.assertIsInstance(f, Finding)


class TestHelperFunctions(unittest.TestCase):
    """내부 헬퍼 함수 테스트."""

    def test_generate_hash_deterministic(self):
        """같은 입력에 같은 해시 반환."""
        h1 = _generate_hash("hello")
        h2 = _generate_hash("hello")
        self.assertEqual(h1, h2)

    def test_generate_hash_different_inputs(self):
        """다른 입력에 다른 해시."""
        h1 = _generate_hash("hello")
        h2 = _generate_hash("world")
        self.assertNotEqual(h1, h2)

    def test_extract_domain(self):
        """쿼리에서 첫 단어 도메인 추출."""
        self.assertEqual(_extract_domain("인공지능 최신 동향"), "인공지능")
        self.assertEqual(_extract_domain("AI trends"), "AI")

    def test_extract_domain_empty(self):
        """빈 쿼리 시 기본값."""
        self.assertEqual(_extract_domain(""), "Technology")

    def test_calculate_relevance_source_weights(self):
        """소스별 관련도 가중치 적용."""
        academic = _calculate_relevance("test", "academic")
        social = _calculate_relevance("test", "social")
        self.assertGreater(academic, social)

    def test_calculate_relevance_max_one(self):
        """관련도가 1.0을 초과하지 않음."""
        # 매우 긴 쿼리
        long_query = "a" * 500
        score = _calculate_relevance(long_query, "academic")
        self.assertLessEqual(score, 1.0)

    def test_create_finding_returns_correct_source(self):
        """_create_finding이 올바른 소스의 Finding 반환."""
        finding = _create_finding("AI", "news")
        self.assertEqual(finding.source, "news")
        self.assertIn("뉴스", finding.content)

    def test_calculate_confidence_empty(self):
        """빈 findings 시 confidence 0."""
        self.assertEqual(_calculate_confidence([], 0), 0.0)

    def test_calculate_confidence_increases_with_sources(self):
        """소스가 많을수록 confidence 증가."""
        findings_2 = [
            _create_finding("test", "academic"),
            _create_finding("test", "news"),
        ]
        findings_5 = [
            _create_finding("test", s) for s in AVAILABLE_SOURCES
        ]
        conf_2 = _calculate_confidence(findings_2, 2)
        conf_5 = _calculate_confidence(findings_5, 5)
        self.assertGreater(conf_5, conf_2)


if __name__ == "__main__":
    unittest.main()
