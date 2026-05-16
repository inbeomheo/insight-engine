"""citation_formatter_service 단위 테스트"""
import unittest

from services.content.citation_formatter_service import (
    format_citation,
    format_bibliography,
    get_citation_styles,
    SUPPORTED_STYLES,
)


class TestFormatCitation(unittest.TestCase):

    def setUp(self):
        self.source = {
            'author': '홍길동',
            'title': '인공지능의 미래',
            'year': '2026',
            'publisher': '한빛미디어',
            'url': 'https://example.com',
        }

    def test_empty_source(self):
        result = format_citation({})
        self.assertEqual(result['formatted'], '')

    def test_none_source(self):
        result = format_citation(None)
        self.assertEqual(result['formatted'], '')

    def test_apa_style(self):
        result = format_citation(self.source, style='apa')
        self.assertIn('홍길동', result['formatted'])
        self.assertIn('(2026)', result['formatted'])
        self.assertEqual(result['style'], 'apa')

    def test_mla_style(self):
        result = format_citation(self.source, style='mla')
        self.assertIn('홍길동', result['formatted'])
        self.assertEqual(result['style'], 'mla')

    def test_chicago_style(self):
        result = format_citation(self.source, style='chicago')
        self.assertIn('한빛미디어', result['formatted'])
        self.assertEqual(result['style'], 'chicago')

    def test_korean_style(self):
        result = format_citation(self.source, style='korean')
        self.assertIn('「인공지능의 미래」', result['formatted'])
        self.assertEqual(result['style'], 'korean')

    def test_journal_article(self):
        source = {
            'author': '김철수',
            'title': '딥러닝 연구',
            'year': '2025',
            'journal': 'AI 학회지',
            'volume': '3',
            'pages': '15-28',
        }
        result = format_citation(source, style='apa')
        self.assertIn('AI 학회지', result['formatted'])

    def test_invalid_style_defaults_apa(self):
        result = format_citation(self.source, style='invalid')
        self.assertEqual(result['style'], 'apa')

    def test_url_included(self):
        result = format_citation(self.source, style='apa')
        self.assertIn('example.com', result['formatted'])

    def test_minimal_source(self):
        result = format_citation({'author': '저자', 'title': '제목'}, style='apa')
        self.assertIn('저자', result['formatted'])
        self.assertIn('제목', result['formatted'])

    def test_type_safety(self):
        source = {'author': 123, 'title': None, 'year': 2026}
        result = format_citation(source, style='apa')
        # None/int → str 변환 처리
        self.assertIsInstance(result['formatted'], str)


class TestFormatBibliography(unittest.TestCase):

    def test_empty(self):
        result = format_bibliography([])
        self.assertEqual(result['total'], 0)

    def test_multiple_sources(self):
        sources = [
            {'author': 'B 저자', 'title': '두 번째 책', 'year': '2025'},
            {'author': 'A 저자', 'title': '첫 번째 책', 'year': '2026'},
        ]
        result = format_bibliography(sources, style='apa')
        self.assertEqual(result['total'], 2)
        # 알파벳 순 정렬 확인
        self.assertTrue(result['entries'][0] < result['entries'][1])

    def test_bibliography_text(self):
        sources = [{'author': '저자', 'title': '제목', 'year': '2026'}]
        result = format_bibliography(sources)
        self.assertGreater(len(result['bibliography']), 0)

    def test_style_propagated(self):
        sources = [{'author': '저자', 'title': '제목'}]
        result = format_bibliography(sources, style='korean')
        self.assertEqual(result['style'], 'korean')


class TestGetCitationStyles(unittest.TestCase):

    def test_returns_all(self):
        styles = get_citation_styles()
        self.assertEqual(len(styles), len(SUPPORTED_STYLES))

    def test_structure(self):
        styles = get_citation_styles()
        for s in styles:
            self.assertIn('id', s)
            self.assertIn('name', s)
            self.assertIn('description', s)


if __name__ == '__main__':
    unittest.main()
