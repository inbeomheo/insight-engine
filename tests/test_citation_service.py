"""citation_service 단위 테스트"""
import unittest

from services.content.citation_service import (
    _timestamp_to_seconds, parse_citations,
    validate_citations, enrich_content_with_links, enrich_html_with_links,
    get_citation_stats, get_citation_density_grade,
)


class TestTimestampToSeconds(unittest.TestCase):
    """_timestamp_to_seconds 테스트"""

    def test_mm_ss(self):
        self.assertEqual(_timestamp_to_seconds('03:25'), 205)

    def test_hh_mm_ss(self):
        self.assertEqual(_timestamp_to_seconds('1:02:30'), 3750)

    def test_zero(self):
        self.assertEqual(_timestamp_to_seconds('0:00'), 0)


class TestParseCitations(unittest.TestCase):
    """parse_citations 테스트"""

    def test_single_citation(self):
        """단일 인용 파싱"""
        result = parse_citations('내용 [03:25] 텍스트')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['marker'], '[03:25]')
        self.assertEqual(result[0]['seconds'], 205)

    def test_multiple_citations(self):
        """다중 인용 파싱"""
        result = parse_citations('[00:30] 시작 [02:15] 중간 [05:00] 끝')
        self.assertEqual(len(result), 3)

    def test_dedup_same_marker(self):
        """동일 마커 중복 제거"""
        result = parse_citations('[01:00] 첫 번째 [01:00] 두 번째')
        self.assertEqual(len(result), 1)

    def test_no_citations(self):
        """인용 없는 텍스트"""
        result = parse_citations('일반 텍스트입니다')
        self.assertEqual(result, [])

    def test_context_extracted(self):
        """주변 컨텍스트 추출"""
        result = parse_citations('앞 텍스트 [03:25] 뒤 텍스트')
        self.assertIn('앞 텍스트', result[0]['context'])


class TestValidateCitations(unittest.TestCase):
    """validate_citations 테스트"""

    def test_valid_citation(self):
        """범위 내 인용은 valid=True"""
        citations = [{'marker': '[01:00]', 'seconds': 60, 'context': ''}]
        segments = [{'start': 0, 'text': 'a'}, {'start': 120, 'text': 'b'}]
        result = validate_citations(citations, segments)
        self.assertTrue(result[0]['valid'])

    def test_invalid_citation(self):
        """범위 밖 인용은 valid=False"""
        citations = [{'marker': '[99:00]', 'seconds': 5940, 'context': ''}]
        segments = [{'start': 0, 'text': 'a'}, {'start': 120, 'text': 'b'}]
        result = validate_citations(citations, segments)
        self.assertFalse(result[0]['valid'])

    def test_no_segments(self):
        """세그먼트 없으면 valid=None"""
        citations = [{'marker': '[01:00]', 'seconds': 60, 'context': ''}]
        result = validate_citations(citations, [])
        self.assertIsNone(result[0]['valid'])


class TestEnrichWithLinks(unittest.TestCase):
    """enrich_content_with_links / enrich_html_with_links 테스트"""

    def test_markdown_link(self):
        """마크다운 링크 변환"""
        result = enrich_content_with_links('참조 [02:30] 입니다', 'abc123')
        self.assertIn('https://youtube.com/watch?v=abc123&t=150s', result)

    def test_html_link(self):
        """HTML 링크 변환"""
        result = enrich_html_with_links('<p>[01:00] 내용</p>', 'xyz')
        self.assertIn('<a href="https://youtube.com/watch?v=xyz&t=60s"', result)
        self.assertIn('target="_blank"', result)

    def test_no_citations_unchanged(self):
        """인용 없으면 변경 없음"""
        text = '일반 텍스트'
        self.assertEqual(enrich_content_with_links(text, 'id'), text)

    def test_html_no_double_wrap(self):
        """HTML 이중 변환 방지: 이미 <a> 태그 내부의 마커는 건너뜀"""
        html = '<p>[03:25] 내용</p>'
        result1 = enrich_html_with_links(html, 'vid1')
        self.assertIn('<a href=', result1)
        # 2차 변환 시 동일해야 함
        result2 = enrich_html_with_links(result1, 'vid1')
        self.assertEqual(result1, result2)

    def test_html_mixed_linked_and_plain(self):
        """HTML에서 이미 링크된 마커와 새 마커가 혼재"""
        html = ('<a href="url" class="citation-link">[01:00]</a> '
                '그리고 [02:00] 도 있음')
        result = enrich_html_with_links(html, 'abc')
        # [01:00]은 이미 링크 → 그대로, [02:00]만 새로 변환
        self.assertEqual(result.count('<a href='), 2)


class TestGetCitationStats(unittest.TestCase):
    """get_citation_stats 테스트"""

    def test_empty_content(self):
        """빈 콘텐츠는 기본값 반환"""
        result = get_citation_stats('')
        self.assertEqual(result['count'], 0)
        self.assertEqual(result['density_per_1000'], 0.0)

    def test_no_citations(self):
        """인용 없는 텍스트"""
        result = get_citation_stats('일반 텍스트입니다')
        self.assertEqual(result['count'], 0)

    def test_count_and_density(self):
        """인용 개수와 밀도 계산"""
        # 100자 텍스트에 인용 2개 → 밀도 약 20/1000자
        text = 'a' * 50 + ' [01:00] ' + 'b' * 40 + ' [02:00] 끝'
        result = get_citation_stats(text)
        self.assertEqual(result['count'], 2)
        self.assertGreater(result['density_per_1000'], 0)

    def test_distribution(self):
        """시간 분포 (전반/중반/후반)"""
        text = '[00:30] 전반 [01:30] 중반 [02:30] 후반'
        result = get_citation_stats(text)
        dist = result['distribution']
        self.assertEqual(dist['early'], 1)
        self.assertEqual(dist['mid'], 1)
        self.assertEqual(dist['late'], 1)

    def test_gap_calculation(self):
        """간격 계산"""
        text = '[01:00] 첫 [03:00] 둘 [04:00] 셋'
        result = get_citation_stats(text)
        # 간격: 120초, 60초 → 평균 90초, 최대 120초
        self.assertEqual(result['avg_gap_seconds'], 90.0)
        self.assertEqual(result['max_gap_seconds'], 120)

    def test_single_citation(self):
        """인용 1개: 간격 없음"""
        result = get_citation_stats('[05:00] 하나만')
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['avg_gap_seconds'], 0.0)
        self.assertEqual(result['max_gap_seconds'], 0)


class TestEnrichContentSkipsExisting(unittest.TestCase):
    """이미 링크화된 마커를 이중 변환하지 않는지 테스트"""

    def test_already_linked_not_doubled(self):
        """이미 마크다운 링크인 마커는 건너뜀"""
        content = '참조 [02:30](https://youtube.com/watch?v=abc&t=150s) 입니다'
        result = enrich_content_with_links(content, 'abc123')
        # 이미 링크가 있으므로 이중 변환되지 않아야 함
        self.assertNotIn('[[02:30]', result)

    def test_plain_marker_still_converted(self):
        """일반 마커는 정상 변환"""
        content = '참조 [02:30] 입니다'
        result = enrich_content_with_links(content, 'abc123')
        self.assertIn('https://youtube.com/watch?v=abc123&t=150s', result)


class TestGetCitationDensityGrade(unittest.TestCase):
    """get_citation_density_grade 테스트"""

    def test_empty_content(self):
        """빈 콘텐츠는 none 등급"""
        result = get_citation_density_grade('')
        self.assertEqual(result['grade'], 'none')
        self.assertEqual(result['citation_count'], 0)

    def test_no_citations(self):
        """인용 없으면 none 등급"""
        result = get_citation_density_grade('일반 텍스트입니다 ' * 100)
        self.assertEqual(result['grade'], 'none')
        self.assertIn('인용이 없습니다', result['suggestion'])

    def test_sparse_grade(self):
        """인용 밀도 낮으면 sparse"""
        # 1000자에 인용 1개 → density ~1.0
        text = 'a' * 990 + ' [01:00] '
        result = get_citation_density_grade(text)
        self.assertEqual(result['grade'], 'sparse')

    def test_moderate_grade(self):
        """적절한 밀도는 moderate"""
        # 200자에 인용 1개 → density ~5.0
        text = 'a' * 190 + ' [01:00] '
        result = get_citation_density_grade(text)
        self.assertEqual(result['grade'], 'moderate')
        self.assertIn('적절한', result['suggestion'])

    def test_dense_grade(self):
        """인용 과다하면 dense"""
        # 50자에 인용 1개 → density ~20.0
        text = 'a' * 40 + ' [01:00] '
        result = get_citation_density_grade(text)
        self.assertEqual(result['grade'], 'dense')

    def test_returns_all_fields(self):
        """반환값에 필수 필드가 모두 포함됨"""
        result = get_citation_density_grade('[01:00] 텍스트')
        for key in ('grade', 'density_per_1000', 'citation_count', 'char_count', 'suggestion'):
            self.assertIn(key, result)


if __name__ == '__main__':
    unittest.main()
