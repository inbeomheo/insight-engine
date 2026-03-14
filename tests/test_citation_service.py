"""citation_service 단위 테스트"""
import unittest

from services.content.citation_service import (
    _timestamp_to_seconds, parse_citations,
    validate_citations, enrich_content_with_links, enrich_html_with_links
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


if __name__ == '__main__':
    unittest.main()
