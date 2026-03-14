"""Parenthetical Overuse Checker 서비스 테스트."""
import unittest
from services.analysis.parenthetical_overuse_service import check_parenthetical_overuse


class TestParentheticalOveruse(unittest.TestCase):

    def test_empty_content(self):
        result = check_parenthetical_overuse('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_parentheticals'], 0)

    def test_none_content(self):
        result = check_parenthetical_overuse(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_parentheses(self):
        content = '이 문장에는 괄호가 없습니다. 깔끔한 글입니다.'
        result = check_parenthetical_overuse(content)
        self.assertEqual(result['summary']['total_parentheticals'], 0)

    def test_moderate_parentheses(self):
        content = '첫 번째 설명 (보충 내용)입니다. 두 번째 문장입니다. 세 번째 문장입니다. 네 번째 문장입니다. 다섯 번째 문장입니다. 여섯 번째 문장입니다. 일곱 번째 문장입니다. 여덟 번째 문장입니다.'
        result = check_parenthetical_overuse(content)
        self.assertEqual(result['summary']['total_parentheticals'], 1)
        self.assertGreaterEqual(result['score'], 70.0)

    def test_excessive_parentheses(self):
        content = '첫째 (보충). 둘째 (설명). 셋째 (참고). 넷째 (주석). 다섯째 (부연).'
        result = check_parenthetical_overuse(content)
        self.assertGreater(result['summary']['total_parentheticals'], 3)

    def test_long_parenthetical(self):
        long_text = 'A' * 35
        content = f'본문 내용입니다 ({long_text}). 다음 문장입니다.'
        result = check_parenthetical_overuse(content)
        self.assertGreater(result['summary']['long_parens'], 0)

    def test_nested_parentheses(self):
        content = '외부 (내부 (중첩된 내용) 계속) 괄호입니다.'
        result = check_parenthetical_overuse(content)
        self.assertGreater(result['summary']['nested_parens'], 0)

    def test_markdown_link_excluded(self):
        content = '[링크 텍스트](https://example.com)는 마크다운 링크입니다. 일반 문장입니다.'
        result = check_parenthetical_overuse(content)
        # 마크다운 링크는 괄호로 카운트되지 않아야 함
        self.assertEqual(result['summary']['total_parentheticals'], 0)

    def test_paren_ratio(self):
        content = '문장 하나 (괄호). 문장 둘입니다. 문장 셋입니다. 문장 넷입니다.'
        result = check_parenthetical_overuse(content)
        self.assertGreater(result['summary']['paren_ratio'], 0.0)
        self.assertLessEqual(result['summary']['paren_ratio'], 100.0)

    def test_high_score_low_ratio(self):
        lines = [f'문장 {i}번째 내용입니다.' for i in range(10)]
        lines[0] = '첫 문장 (간단한 보충)입니다.'
        content = ' '.join(lines)
        result = check_parenthetical_overuse(content)
        self.assertGreaterEqual(result['score'], 80.0)

    def test_suggestions_no_parens(self):
        content = '괄호 없는 깨끗한 글입니다. 간결합니다.'
        result = check_parenthetical_overuse(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_suggestions_overuse(self):
        content = '하나 (가). 둘 (나). 셋 (다). 넷 (라). 다섯 (마).'
        result = check_parenthetical_overuse(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '테스트 (괄호) 콘텐츠입니다.'
        result = check_parenthetical_overuse(content)
        self.assertIn('parentheticals', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_parentheticals', result['summary'])
        self.assertIn('paren_ratio', result['summary'])
        self.assertIn('long_parens', result['summary'])
        self.assertIn('nested_parens', result['summary'])


if __name__ == '__main__':
    unittest.main()
