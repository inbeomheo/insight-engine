"""Whitespace Formatting Auditor 서비스 테스트."""
import unittest
from services.whitespace_formatting_service import audit_whitespace_formatting


class TestWhitespaceFormattingAuditor(unittest.TestCase):

    def test_empty_content(self):
        result = audit_whitespace_formatting('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_issues'], 0)

    def test_none_content(self):
        result = audit_whitespace_formatting(None)
        self.assertEqual(result['score'], 100.0)

    def test_clean_content(self):
        content = '첫 줄입니다.\n\n둘째 줄입니다.\n\n셋째 줄입니다.'
        result = audit_whitespace_formatting(content)
        self.assertEqual(result['summary']['consecutive_blanks'], 0)

    def test_consecutive_blank_lines(self):
        content = '첫 줄입니다.\n\n\n\n\n둘째 줄입니다.'
        result = audit_whitespace_formatting(content)
        self.assertGreater(result['summary']['consecutive_blanks'], 0)

    def test_trailing_spaces(self):
        content = '줄 끝에 공백   \n다음 줄'
        result = audit_whitespace_formatting(content)
        self.assertGreater(result['summary']['trailing_spaces'], 0)

    def test_mixed_indent(self):
        content = '\t탭 들여쓰기\n    스페이스 들여쓰기'
        result = audit_whitespace_formatting(content)
        self.assertEqual(result['summary']['inconsistent_indent'], 1)

    def test_long_lines(self):
        content = '가' * 250 + '\n짧은 줄'
        result = audit_whitespace_formatting(content)
        has_long = any(i['type'] == 'long_lines' for i in result['issues'])
        self.assertTrue(has_long)

    def test_heading_spacing(self):
        content = '텍스트 줄입니다.\n## 헤딩\n내용입니다.'
        result = audit_whitespace_formatting(content)
        has_heading = any(i['type'] == 'heading_spacing' for i in result['issues'])
        self.assertTrue(has_heading)

    def test_heading_with_blank_no_issue(self):
        content = '텍스트 줄입니다.\n\n## 헤딩\n내용입니다.'
        result = audit_whitespace_formatting(content)
        has_heading = any(i['type'] == 'heading_spacing' for i in result['issues'])
        self.assertFalse(has_heading)

    def test_code_block_excluded_from_long_lines(self):
        content = '```python\n' + 'x' * 250 + '\n```\n짧은 줄'
        result = audit_whitespace_formatting(content)
        has_long = any(i['type'] == 'long_lines' for i in result['issues'])
        self.assertFalse(has_long)

    def test_score_decreases_with_issues(self):
        content = '줄   \n\n\n\n\n\n빈줄 많음\n\t탭\n    스페이스'
        result = audit_whitespace_formatting(content)
        self.assertLess(result['score'], 100.0)

    def test_suggestions_for_blanks(self):
        content = '첫줄\n\n\n\n\n둘째줄'
        result = audit_whitespace_formatting(content)
        self.assertTrue(any('빈 줄' in s for s in result['suggestions']))

    def test_suggestions_clean(self):
        content = '깨끗한 텍스트입니다.\n\n다음 문단입니다.'
        result = audit_whitespace_formatting(content)
        if result['suggestions']:
            self.assertTrue(any('일관' in s or '문제' in s for s in result['suggestions']))

    def test_return_structure(self):
        content = '테스트 콘텐츠입니다.'
        result = audit_whitespace_formatting(content)
        self.assertIn('issues', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_issues', result['summary'])
        self.assertIn('total_lines', result['summary'])


if __name__ == '__main__':
    unittest.main()
