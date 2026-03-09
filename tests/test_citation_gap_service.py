"""citation_gap_service 단위 테스트"""
import unittest

from services.citation_gap_service import (
    find_citation_gaps,
    GapOpportunity,
    _count_citations_in_text,
    _extract_topics_from_text,
    _extract_topics_from_citations,
    _count_our_citations_by_topic,
    _calculate_gap_score,
    _ensure_minimum_gaps,
)


class TestCountCitationsInText(unittest.TestCase):
    """_count_citations_in_text 함수 테스트"""

    def test_bracket_citations(self):
        """[숫자] 형식 인용 감지"""
        text = '연구에 따르면 [1] 그리고 [2] 이러한 결과가 나왔다 [3].'
        self.assertEqual(_count_citations_in_text(text), 3)

    def test_source_citation_korean(self):
        """(출처: ...) 형식 감지"""
        text = '데이터에 의하면 (출처: 한국은행 보고서) 성장률이 높다.'
        self.assertEqual(_count_citations_in_text(text), 1)

    def test_url_citation(self):
        """URL 인용 감지"""
        text = '참고: https://example.com/report 에서 확인 가능.'
        self.assertEqual(_count_citations_in_text(text), 1)

    def test_korean_book_citation(self):
        """한국어 서명 인용 「...」"""
        text = '「디지털 마케팅 전략」에 따르면'
        self.assertEqual(_count_citations_in_text(text), 1)

    def test_no_citations(self):
        """인용 없는 텍스트"""
        text = '일반적인 텍스트입니다. 인용이 없습니다.'
        self.assertEqual(_count_citations_in_text(text), 0)

    def test_mixed_citations(self):
        """혼합 인용 형식"""
        text = '[1] 연구와 (출처: ABC) 그리고 https://test.com 참고'
        self.assertEqual(_count_citations_in_text(text), 3)


class TestExtractTopicsFromText(unittest.TestCase):
    """_extract_topics_from_text 함수 테스트"""

    def test_heading_extraction(self):
        """마크다운 헤딩에서 주제 추출"""
        text = '## 인공지능의 미래\n\n내용...\n\n## 머신러닝 기초'
        topics = _extract_topics_from_text(text)
        self.assertTrue(any('인공지능' in t for t in topics))

    def test_bold_extraction(self):
        """굵은 글씨에서 주제 추출"""
        text = '이 분야에서 **딥러닝 기술**은 매우 중요합니다.'
        topics = _extract_topics_from_text(text)
        self.assertTrue(any('딥러닝 기술' in t for t in topics))

    def test_frequency_based(self):
        """빈도 기반 키워드 추출 (3회 이상)"""
        text = '블록체인 기술은 혁신입니다. 블록체인 보안이 중요합니다. 블록체인 활용 사례.'
        topics = _extract_topics_from_text(text)
        self.assertTrue(any('블록체인' in t for t in topics))

    def test_empty_text(self):
        """빈 텍스트"""
        topics = _extract_topics_from_text('')
        self.assertEqual(topics, [])


class TestExtractTopicsFromCitations(unittest.TestCase):
    """_extract_topics_from_citations 함수 테스트"""

    def test_with_citation_count(self):
        """citation_count 필드 사용"""
        data = [
            {'topic': 'AI 기술', 'citation_count': 5},
            {'topic': 'AI 기술', 'citation_count': 3},
        ]
        result = _extract_topics_from_citations(data)
        self.assertEqual(result['AI 기술'], 8)

    def test_with_content(self):
        """content 필드에서 인용 수 추출"""
        data = [{'topic': 'SEO', 'content': '연구 [1] 참고 [2]'}]
        result = _extract_topics_from_citations(data)
        self.assertEqual(result['SEO'], 2)

    def test_empty_topic_skipped(self):
        """빈 주제 무시"""
        data = [{'topic': '', 'citation_count': 5}]
        result = _extract_topics_from_citations(data)
        self.assertEqual(len(result), 0)

    def test_no_count_no_content(self):
        """count도 content도 없으면 기본값 1"""
        data = [{'topic': '테스트'}]
        result = _extract_topics_from_citations(data)
        self.assertEqual(result['테스트'], 1)


class TestCountOurCitationsByTopic(unittest.TestCase):
    """_count_our_citations_by_topic 함수 테스트"""

    def test_topic_in_paragraph_with_citation(self):
        """주제가 포함된 문단 내 인용 카운트"""
        content = ['AI 기술에 대해 [1] 설명합니다.\n\n다른 주제 내용.']
        result = _count_our_citations_by_topic(content, ['AI 기술'])
        self.assertEqual(result['AI 기술'], 1)

    def test_topic_not_found(self):
        """주제가 콘텐츠에 없는 경우"""
        content = ['완전히 다른 내용입니다.']
        result = _count_our_citations_by_topic(content, ['블록체인'])
        self.assertEqual(result['블록체인'], 0)


class TestCalculateGapScore(unittest.TestCase):
    """_calculate_gap_score 함수 테스트"""

    def test_full_gap(self):
        """경쟁사만 인용, 우리는 0"""
        score = _calculate_gap_score(5, 0)
        self.assertGreater(score, 0.5)
        self.assertLessEqual(score, 1.0)

    def test_no_gap(self):
        """동일한 인용 수"""
        score = _calculate_gap_score(5, 5)
        self.assertEqual(score, 0.0)

    def test_zero_competitor(self):
        """경쟁사 인용 0"""
        score = _calculate_gap_score(0, 3)
        self.assertEqual(score, 0.0)

    def test_partial_gap(self):
        """부분 갭"""
        score = _calculate_gap_score(10, 3)
        self.assertGreater(score, 0)
        self.assertLess(score, 1.0)

    def test_our_exceeds_competitor(self):
        """우리 인용이 경쟁사보다 많은 경우"""
        score = _calculate_gap_score(3, 10)
        self.assertEqual(score, 0.0)


class TestEnsureMinimumGaps(unittest.TestCase):
    """_ensure_minimum_gaps 함수 테스트"""

    def test_less_than_3_gaps(self):
        """3개 미만이면 기본 권장사항 추가"""
        gaps = [
            GapOpportunity('토픽1', 5, 0, 0.8, '추천1'),
        ]
        result = _ensure_minimum_gaps(gaps, ['일부 콘텐츠'])
        self.assertGreaterEqual(len(result), 3)

    def test_already_3_or_more(self):
        """3개 이상이면 추가하지 않음"""
        gaps = [
            GapOpportunity('토픽1', 5, 0, 0.8, '추천1'),
            GapOpportunity('토픽2', 3, 1, 0.5, '추천2'),
            GapOpportunity('토픽3', 4, 2, 0.3, '추천3'),
        ]
        result = _ensure_minimum_gaps(gaps, [])
        self.assertEqual(len(result), 3)

    def test_empty_gaps(self):
        """빈 목록도 3개 보장"""
        result = _ensure_minimum_gaps([], None)
        self.assertGreaterEqual(len(result), 3)


class TestFindCitationGaps(unittest.TestCase):
    """find_citation_gaps 통합 테스트"""

    def test_basic_gap_detection(self):
        """기본 갭 탐지"""
        our_content = ['AI 기술에 대한 일반적인 설명입니다.']
        competitor_citations = [
            {'topic': 'AI 기술', 'citation_count': 5},
            {'topic': '데이터 분석', 'citation_count': 3},
        ]
        result = find_citation_gaps(our_content, competitor_citations)
        self.assertGreaterEqual(len(result), 3)
        self.assertIsInstance(result[0], GapOpportunity)

    def test_minimum_3_gaps_guaranteed(self):
        """최소 3개 갭 보장"""
        result = find_citation_gaps([], [])
        self.assertGreaterEqual(len(result), 3)

    def test_sorted_by_gap_score(self):
        """gap_score 내림차순 정렬"""
        our_content = ['일반 텍스트']
        competitor_citations = [
            {'topic': '주제A', 'citation_count': 10},
            {'topic': '주제B', 'citation_count': 2},
            {'topic': '주제C', 'citation_count': 7},
        ]
        result = find_citation_gaps(our_content, competitor_citations)
        scores = [g.gap_score for g in result]
        # 상위 항목이 하위보다 크거나 같아야 함
        for i in range(len(scores) - 1):
            self.assertGreaterEqual(scores[i], scores[i + 1])

    def test_gap_opportunity_fields(self):
        """GapOpportunity 필드 존재 확인"""
        result = find_citation_gaps(
            ['콘텐츠'],
            [{'topic': '테스트', 'citation_count': 3}],
        )
        gap = result[0]
        self.assertTrue(hasattr(gap, 'topic'))
        self.assertTrue(hasattr(gap, 'competitor_citations'))
        self.assertTrue(hasattr(gap, 'our_citations'))
        self.assertTrue(hasattr(gap, 'gap_score'))
        self.assertTrue(hasattr(gap, 'recommendation'))

    def test_recommendation_not_empty(self):
        """추천 메시지가 항상 비어 있지 않음"""
        result = find_citation_gaps(
            ['콘텐츠'],
            [{'topic': 'SEO', 'citation_count': 5}],
        )
        for gap in result:
            self.assertTrue(len(gap.recommendation) > 0)

    def test_with_content_field(self):
        """content 필드 기반 경쟁사 데이터"""
        our_content = ['SEO 관련 글']
        competitor_citations = [
            {'topic': 'SEO', 'content': '연구 [1] 데이터 [2] 분석 [3] 결과 [4]'},
        ]
        result = find_citation_gaps(our_content, competitor_citations)
        # SEO 주제가 결과에 포함되어야 함
        seo_gaps = [g for g in result if 'SEO' in g.topic.upper()]
        self.assertGreater(len(seo_gaps), 0)

    def test_gap_score_range(self):
        """gap_score가 0~1 범위"""
        result = find_citation_gaps(
            ['텍스트'],
            [{'topic': '주제', 'citation_count': 100}],
        )
        for gap in result:
            self.assertGreaterEqual(gap.gap_score, 0.0)
            self.assertLessEqual(gap.gap_score, 1.0)


if __name__ == '__main__':
    unittest.main()
