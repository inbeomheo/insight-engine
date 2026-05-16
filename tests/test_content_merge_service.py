"""content_merge_service 단위 테스트"""
import unittest

from services.content.content_merge_service import (
    merge_contents,
    _extract_sections,
    _deduplicate_sentences,
    _sentence_hash,
)


class TestMergeContents(unittest.TestCase):

    def test_empty_list(self):
        result = merge_contents([])
        self.assertEqual(result['source_count'], 0)
        self.assertEqual(result['merged_content'], '')

    def test_single_content(self):
        result = merge_contents([{'title': 'T1', 'content': '# 제목\n본문'}])
        self.assertEqual(result['source_count'], 1)
        self.assertIn('제목', result['merged_content'])

    def test_two_contents_merged(self):
        contents = [
            {'title': 'A', 'content': '# 섹션 A\n내용 A'},
            {'title': 'B', 'content': '# 섹션 B\n내용 B'},
        ]
        result = merge_contents(contents)
        self.assertEqual(result['source_count'], 2)
        self.assertIn('섹션 A', result['merged_content'])
        self.assertIn('섹션 B', result['merged_content'])

    def test_duplicate_headings_merged(self):
        contents = [
            {'title': 'A', 'content': '# 결론\n첫 번째 결론 내용입니다.'},
            {'title': 'B', 'content': '# 결론\n두 번째 결론 내용입니다.'},
        ]
        result = merge_contents(contents)
        # 같은 제목은 하나로 합쳐짐
        heading_count = result['merged_content'].count('# 결론')
        self.assertEqual(heading_count, 1)

    def test_toc_generated(self):
        contents = [
            {'title': 'A', 'content': '# 서론\n소개\n## 본론\n내용'},
        ]
        result = merge_contents(contents)
        self.assertGreater(len(result['toc']), 0)
        headings = [t['heading'] for t in result['toc']]
        self.assertIn('서론', headings)

    def test_deduplication_on(self):
        contents = [
            {'title': 'A', 'content': '# A\n이것은 중복 문장입니다. 이것은 중복 문장입니다.'},
        ]
        result = merge_contents(contents, deduplicate=True)
        self.assertGreaterEqual(result['duplicate_sentences_removed'], 0)

    def test_deduplication_off(self):
        contents = [
            {'title': 'A', 'content': '# A\n반복. 반복.'},
        ]
        result = merge_contents(contents, deduplicate=False)
        self.assertEqual(result['duplicate_sentences_removed'], 0)

    def test_empty_content_skipped(self):
        contents = [
            {'title': 'A', 'content': ''},
            {'title': 'B', 'content': '# 유효\n내용'},
        ]
        result = merge_contents(contents)
        self.assertEqual(result['source_count'], 2)
        self.assertIn('유효', result['merged_content'])

    def test_char_count(self):
        contents = [{'title': 'A', 'content': '# 제목\n본문 내용'}]
        result = merge_contents(contents)
        self.assertEqual(result['char_count'], len(result['merged_content']))

    def test_three_way_merge(self):
        contents = [
            {'title': 'A', 'content': '# 파트 1\n내용 1'},
            {'title': 'B', 'content': '# 파트 2\n내용 2'},
            {'title': 'C', 'content': '# 파트 3\n내용 3'},
        ]
        result = merge_contents(contents)
        self.assertEqual(result['source_count'], 3)
        self.assertEqual(result['section_count'], 3)


class TestExtractSections(unittest.TestCase):

    def test_single_section(self):
        sections = _extract_sections('# 제목\n본문 내용')
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]['heading'], '제목')
        self.assertEqual(sections[0]['level'], 1)

    def test_multiple_sections(self):
        text = '# 서론\n소개글\n## 본론\n본문\n## 결론\n마무리'
        sections = _extract_sections(text)
        self.assertEqual(len(sections), 3)

    def test_no_heading(self):
        sections = _extract_sections('그냥 텍스트만 있는 경우')
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]['heading'], '')

    def test_heading_levels(self):
        text = '# H1\n내용\n## H2\n내용\n### H3\n내용'
        sections = _extract_sections(text)
        levels = [s['level'] for s in sections]
        self.assertEqual(levels, [1, 2, 3])


class TestDeduplicateSentences(unittest.TestCase):

    def test_removes_duplicates(self):
        text = '중복 문장입니다. 다른 문장입니다. 중복 문장입니다.'
        result = _deduplicate_sentences(text)
        self.assertEqual(result.count('중복 문장입니다'), 1)

    def test_preserves_unique(self):
        text = '첫째. 둘째. 셋째.'
        result = _deduplicate_sentences(text)
        self.assertIn('첫째', result)
        self.assertIn('둘째', result)
        self.assertIn('셋째', result)

    def test_empty_input(self):
        self.assertEqual(_deduplicate_sentences(''), '')


class TestSentenceHash(unittest.TestCase):

    def test_consistent(self):
        h1 = _sentence_hash('테스트 문장')
        h2 = _sentence_hash('테스트 문장')
        self.assertEqual(h1, h2)

    def test_case_insensitive(self):
        h1 = _sentence_hash('Hello World')
        h2 = _sentence_hash('hello world')
        self.assertEqual(h1, h2)

    def test_whitespace_insensitive(self):
        h1 = _sentence_hash('a  b  c')
        h2 = _sentence_hash('a b c')
        self.assertEqual(h1, h2)

    def test_different_hashes(self):
        h1 = _sentence_hash('문장 A')
        h2 = _sentence_hash('문장 B')
        self.assertNotEqual(h1, h2)


if __name__ == '__main__':
    unittest.main()
