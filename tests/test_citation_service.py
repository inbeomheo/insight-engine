"""citation_service 단위 테스트"""
import unittest

from services.content.citation_service import (
    _timestamp_to_seconds, parse_citations,
    validate_citations, enrich_content_with_links, enrich_html_with_links,
    build_source_receipts,
)


class TestTimestampToSeconds(unittest.TestCase):
    """_timestamp_to_seconds 테스트"""

    def test_mm_ss(self):
        self.assertEqual(_timestamp_to_seconds('03:25'), 205)

    def test_hh_mm_ss(self):
        self.assertEqual(_timestamp_to_seconds('1:02:30'), 3750)

    def test_zero(self):
        self.assertEqual(_timestamp_to_seconds('0:00'), 0)

    def test_decimal_seconds_mm_ss(self):
        """소수점 초 (일부 자막 형식)를 정수로 변환"""
        self.assertEqual(_timestamp_to_seconds('1:30.5'), 90)

    def test_decimal_seconds_hh_mm_ss(self):
        """HH:MM:SS.ms 형식의 소수점 초"""
        self.assertEqual(_timestamp_to_seconds('0:01:30.9'), 90)

    def test_invalid_empty_string(self):
        """빈 문자열은 0 반환"""
        self.assertEqual(_timestamp_to_seconds(''), 0)

    def test_single_number(self):
        """콜론 없는 숫자는 0 반환"""
        self.assertEqual(_timestamp_to_seconds('30'), 0)

    def test_four_parts(self):
        """4개 파트는 0 반환"""
        self.assertEqual(_timestamp_to_seconds('1:2:3:4'), 0)

    def test_seconds_out_of_range(self):
        """초가 60 이상이면 0 반환"""
        self.assertEqual(_timestamp_to_seconds('1:60'), 0)

    def test_minutes_out_of_range_in_hhmmss(self):
        """HH:MM:SS에서 분이 60 이상이면 0 반환"""
        self.assertEqual(_timestamp_to_seconds('1:60:00'), 0)

    def test_non_numeric(self):
        """문자열이 포함된 경우 0 반환"""
        self.assertEqual(_timestamp_to_seconds('ab:cd'), 0)


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
        result = enrich_content_with_links('참조 [02:30] 입니다', 'dQw4w9WgXcQ')
        self.assertIn('https://youtube.com/watch?v=dQw4w9WgXcQ&t=150s', result)

    def test_html_link(self):
        """HTML 링크 변환"""
        result = enrich_html_with_links('<p>[01:00] 내용</p>', 'dQw4w9WgXcQ')
        self.assertIn('<a href="https://youtube.com/watch?v=dQw4w9WgXcQ&t=60s"', result)
        self.assertIn('target="_blank"', result)

    def test_no_citations_unchanged(self):
        """인용 없으면 변경 없음"""
        text = '일반 텍스트'
        self.assertEqual(enrich_content_with_links(text, 'dQw4w9WgXcQ'), text)

    def test_html_no_double_wrap(self):
        """HTML 이중 변환 방지: 이미 <a> 태그 내부의 마커는 건너뜀"""
        html = '<p>[03:25] 내용</p>'
        result1 = enrich_html_with_links(html, 'dQw4w9WgXcQ')
        self.assertIn('<a href=', result1)
        # 2차 변환 시 동일해야 함
        result2 = enrich_html_with_links(result1, 'dQw4w9WgXcQ')
        self.assertEqual(result1, result2)

    def test_html_mixed_linked_and_plain(self):
        """HTML에서 이미 링크된 마커와 새 마커가 혼재"""
        html = ('<a href="url" class="citation-link">[01:00]</a> '
                '그리고 [02:00] 도 있음')
        result = enrich_html_with_links(html, 'dQw4w9WgXcQ')
        # [01:00]은 이미 링크 → 그대로, [02:00]만 새로 변환
        self.assertEqual(result.count('<a href='), 2)


class TestEnrichContentSkipsExisting(unittest.TestCase):
    """이미 링크화된 마커를 이중 변환하지 않는지 테스트"""

    def test_already_linked_not_doubled(self):
        """이미 마크다운 링크인 마커는 건너뜀"""
        content = '참조 [02:30](https://youtube.com/watch?v=abc&t=150s) 입니다'
        result = enrich_content_with_links(content, 'dQw4w9WgXcQ')
        # 이미 링크가 있으므로 이중 변환되지 않아야 함
        self.assertNotIn('[[02:30]', result)

    def test_plain_marker_still_converted(self):
        """일반 마커는 정상 변환"""
        content = '참조 [02:30] 입니다'
        result = enrich_content_with_links(content, 'dQw4w9WgXcQ')
        self.assertIn('https://youtube.com/watch?v=dQw4w9WgXcQ&t=150s', result)

    def test_invalid_video_id_raises(self):
        """유효하지 않은 video_id는 ValueError 발생"""
        with self.assertRaises(ValueError):
            enrich_content_with_links('[01:00] 텍스트', 'short')

    def test_invalid_video_id_html_raises(self):
        """HTML 변환 시 유효하지 않은 video_id는 ValueError 발생"""
        with self.assertRaises(ValueError):
            enrich_html_with_links('<p>[01:00]</p>', '')


class TestBuildSourceReceipts(unittest.TestCase):
    """build_source_receipts 테스트"""

    def test_builds_claim_timestamp_and_collected_at(self):
        citations = [{
            'marker': '[02:30]',
            'seconds': 150,
            'context': '핵심 주장은 [02:30] 여기에서 확인됩니다.',
            'valid': True,
        }]

        result = build_source_receipts(
            citations,
            'dQw4w9WgXcQ',
            '2026-07-08T00:00:00+00:00',
            source_title='테스트 영상',
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['claim'], '핵심 주장은 여기에서 확인됩니다.')
        self.assertEqual(result[0]['timestamp_url'], 'https://youtube.com/watch?v=dQw4w9WgXcQ&t=150s')
        self.assertEqual(result[0]['collected_at'], '2026-07-08T00:00:00+00:00')
        self.assertEqual(result[0]['source']['type'], 'youtube')
        self.assertEqual(result[0]['source']['title'], '테스트 영상')
        self.assertTrue(result[0]['valid'])

    def test_linked_marker_is_removed_from_claim(self):
        citations = [{
            'marker': '[01:00]',
            'seconds': 60,
            'context': '주장은 [01:00](https://youtube.com/watch?v=dQw4w9WgXcQ&t=60s) 근거입니다.',
        }]

        result = build_source_receipts(citations, 'dQw4w9WgXcQ', '2026-07-08T00:00:00+00:00')

        self.assertEqual(result[0]['claim'], '주장은 근거입니다.')

    def test_deduplicates_same_marker_and_seconds(self):
        citations = [
            {'marker': '[01:00]', 'seconds': 60, 'context': 'A [01:00]'},
            {'marker': '[01:00]', 'seconds': 60, 'context': 'B [01:00]'},
        ]

        result = build_source_receipts(citations, 'dQw4w9WgXcQ', '2026-07-08T00:00:00+00:00')

        self.assertEqual(len(result), 1)

    def test_invalid_video_id_raises(self):
        with self.assertRaises(ValueError):
            build_source_receipts([], 'bad', '2026-07-08T00:00:00+00:00')


if __name__ == '__main__':
    unittest.main()
