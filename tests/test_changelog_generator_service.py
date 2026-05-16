"""changelog_generator_service 단위 테스트"""
import unittest

from services.content.changelog_generator_service import (
    generate_changelog,
    _categorize_change,
    _summarize_diff_stats,
)


class TestGenerateChangelog(unittest.TestCase):

    def test_empty(self):
        result = generate_changelog([])
        self.assertEqual(result['total_entries'], 0)

    def test_single_entry(self):
        entries = [{'version': 'v1.0', 'date': '2026-01-01', 'changes': ['기능 추가']}]
        result = generate_changelog(entries)
        self.assertEqual(result['total_entries'], 1)
        self.assertIn('v1.0', result['changelog_md'])
        self.assertIn('기능 추가', result['changelog_md'])

    def test_multiple_entries(self):
        entries = [
            {'version': 'v2.0', 'date': '2026-02-01', 'changes': ['대규모 업데이트']},
            {'version': 'v1.0', 'date': '2026-01-01', 'changes': ['최초 릴리스']},
        ]
        result = generate_changelog(entries)
        self.assertEqual(result['total_entries'], 2)
        self.assertEqual(result['total_changes'], 2)

    def test_author_included(self):
        entries = [{'version': 'v1.0', 'date': '2026-01-01', 'changes': ['변경'], 'author': '홍길동'}]
        result = generate_changelog(entries)
        self.assertIn('홍길동', result['changelog_md'])

    def test_diff_stats_auto_summary(self):
        entries = [{'version': 'v1.1', 'date': '2026-01-15',
                    'diff_stats': {'additions': 10, 'deletions': 3, 'modifications': 5}}]
        result = generate_changelog(entries)
        self.assertIn('추가', result['changelog_md'])
        self.assertIn('삭제', result['changelog_md'])

    def test_text_format(self):
        entries = [{'version': 'v1.0', 'date': '2026-01-01', 'changes': ['변경1']}]
        result = generate_changelog(entries)
        self.assertGreater(len(result['changelog_text']), 0)
        self.assertNotIn('#', result['changelog_text'])

    def test_custom_title(self):
        entries = [{'version': 'v1.0', 'changes': ['변경']}]
        result = generate_changelog(entries, title='릴리스 노트')
        self.assertIn('릴리스 노트', result['changelog_md'])

    def test_total_changes_count(self):
        entries = [{'version': 'v1.0', 'changes': ['A', 'B', 'C']}]
        result = generate_changelog(entries)
        self.assertEqual(result['total_changes'], 3)


class TestCategorizeChange(unittest.TestCase):

    def test_addition(self):
        result = _categorize_change('새 기능 추가')
        self.assertIn('**추가**', result)

    def test_fix(self):
        result = _categorize_change('버그 수정')
        self.assertIn('**수정**', result)

    def test_deletion(self):
        result = _categorize_change('레거시 코드 삭제')
        self.assertIn('**삭제**', result)

    def test_uncategorized(self):
        result = _categorize_change('기타 작업')
        self.assertNotIn('**', result)


class TestSummarizeDiffStats(unittest.TestCase):

    def test_all_stats(self):
        result = _summarize_diff_stats({'additions': 5, 'deletions': 2, 'modifications': 3})
        self.assertEqual(len(result), 3)

    def test_empty_stats(self):
        result = _summarize_diff_stats({})
        self.assertIn('변경사항 없음', result)

    def test_partial_stats(self):
        result = _summarize_diff_stats({'additions': 10})
        self.assertEqual(len(result), 1)
        self.assertIn('추가', result[0])


if __name__ == '__main__':
    unittest.main()
