"""structure_analyzer_service 단위 테스트"""
import unittest

from services.content.structure_analyzer_service import (
    analyze_structure,
    _build_heading_tree,
    _split_by_headings,
    _calculate_balance,
    _check_completeness,
    _count_elements,
    _detect_issues,
)


class TestAnalyzeStructure(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_structure('')
        self.assertEqual(result['heading_tree'], [])
        self.assertEqual(result['completeness']['score'], 0.0)

    def test_none_content(self):
        result = analyze_structure(None)
        self.assertEqual(result['heading_tree'], [])

    def test_well_structured(self):
        content = """# 서론

도입 내용이 여기 있습니다. 충분한 내용을 담고 있습니다.

## 본론

본문 내용이 여기 있습니다. 자세한 설명을 제공합니다.

## 결론

마무리 내용입니다. 정리하면 이렇습니다."""
        result = analyze_structure(content)
        self.assertGreater(result['completeness']['score'], 0.5)
        self.assertTrue(result['completeness']['has_headings'])
        self.assertTrue(result['completeness']['has_hierarchy'])

    def test_no_headings(self):
        content = '헤딩 없는 긴 텍스트입니다. ' * 30
        result = analyze_structure(content)
        self.assertEqual(len(result['heading_tree']), 0)
        self.assertFalse(result['completeness']['has_headings'])

    def test_issues_detected(self):
        # 200단어 이상 + 헤딩 없음 → 이슈 감지
        content = ' '.join([f'단어{i}' for i in range(250)])
        result = analyze_structure(content)
        self.assertGreater(len(result['issues']), 0)

    def test_element_counts(self):
        content = """# 제목

- 항목 1
- 항목 2

![이미지](url)

[링크](url)

```python
code
```"""
        result = analyze_structure(content)
        counts = result['element_counts']
        self.assertEqual(counts['headings'], 1)
        self.assertEqual(counts['list_items'], 2)
        self.assertEqual(counts['images'], 1)
        # 이미지 마크다운 ![](url)도 링크 패턴에 매칭될 수 있음
        self.assertGreaterEqual(counts['links'], 1)
        self.assertEqual(counts['code_blocks'], 1)


class TestBuildHeadingTree(unittest.TestCase):

    def test_single_heading(self):
        tree = _build_heading_tree('# 제목')
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree[0]['level'], 1)
        self.assertEqual(tree[0]['text'], '제목')

    def test_multi_level(self):
        text = '# H1\n## H2\n### H3'
        tree = _build_heading_tree(text)
        self.assertEqual(len(tree), 3)
        levels = [h['level'] for h in tree]
        self.assertEqual(levels, [1, 2, 3])

    def test_no_headings(self):
        tree = _build_heading_tree('일반 텍스트')
        self.assertEqual(tree, [])

    def test_word_count(self):
        tree = _build_heading_tree('# 세 개 단어')
        self.assertEqual(tree[0]['word_count'], 3)


class TestSplitByHeadings(unittest.TestCase):

    def test_basic_split(self):
        text = '# A\n내용A\n# B\n내용B'
        sections = _split_by_headings(text)
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0]['heading'], 'A')

    def test_intro_without_heading(self):
        text = '도입 텍스트\n# 본문\n내용'
        sections = _split_by_headings(text)
        self.assertEqual(sections[0]['heading'], '(도입부)')

    def test_empty_section(self):
        text = '# 빈섹션\n# 다음섹션\n내용'
        sections = _split_by_headings(text)
        empty = [s for s in sections if s['word_count'] == 0]
        self.assertGreater(len(empty), 0)


class TestCalculateBalance(unittest.TestCase):

    def test_single_section(self):
        result = _calculate_balance([{'heading': 'A', 'word_count': 100, 'level': 1, 'body': ''}])
        self.assertEqual(result['score'], 1.0)

    def test_balanced(self):
        sections = [
            {'heading': 'A', 'word_count': 100, 'level': 1, 'body': ''},
            {'heading': 'B', 'word_count': 110, 'level': 1, 'body': ''},
            {'heading': 'C', 'word_count': 95, 'level': 1, 'body': ''},
        ]
        result = _calculate_balance(sections)
        self.assertGreater(result['score'], 0.8)

    def test_unbalanced(self):
        sections = [
            {'heading': 'A', 'word_count': 500, 'level': 1, 'body': ''},
            {'heading': 'B', 'word_count': 10, 'level': 1, 'body': ''},
        ]
        result = _calculate_balance(sections)
        self.assertLess(result['score'], 0.8)

    def test_details_include_status(self):
        sections = [
            {'heading': 'A', 'word_count': 500, 'level': 1, 'body': ''},
            {'heading': 'B', 'word_count': 10, 'level': 1, 'body': ''},
        ]
        result = _calculate_balance(sections)
        statuses = [d['status'] for d in result['details']]
        self.assertTrue('too_long' in statuses or 'too_short' in statuses)


class TestDetectIssues(unittest.TestCase):

    def test_heading_level_skip(self):
        tree = [
            {'level': 1, 'text': 'H1', 'word_count': 1},
            {'level': 3, 'text': 'H3', 'word_count': 1},
        ]
        issues = _detect_issues(tree, [], {'headings': 2, 'total_words': 50, 'list_items': 0, 'paragraphs': 2})
        self.assertTrue(any('건너뛰기' in i for i in issues))

    def test_empty_section(self):
        sections = [{'heading': '빈섹션', 'level': 1, 'body': '', 'word_count': 0}]
        issues = _detect_issues([], sections, {'headings': 1, 'total_words': 0, 'list_items': 0, 'paragraphs': 0})
        self.assertTrue(any('빈 섹션' in i for i in issues))

    def test_no_issues(self):
        tree = [{'level': 1, 'text': 'H1', 'word_count': 1}]
        sections = [{'heading': 'H1', 'level': 1, 'body': '내용', 'word_count': 10}]
        elements = {'headings': 1, 'total_words': 10, 'list_items': 0, 'paragraphs': 1}
        issues = _detect_issues(tree, sections, elements)
        self.assertEqual(issues, [])


if __name__ == '__main__':
    unittest.main()
