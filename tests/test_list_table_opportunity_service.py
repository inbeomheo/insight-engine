"""List/Table Opportunity Detector 서비스 테스트."""
import unittest
from services.analysis.list_table_opportunity_service import detect_list_table_opportunities


class TestListTableOpportunityDetector(unittest.TestCase):
    """detect_list_table_opportunities 함수 테스트."""

    def test_empty_content(self):
        result = detect_list_table_opportunities('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_opportunities'], 0)
        self.assertEqual(result['opportunities'], [])

    def test_none_content(self):
        result = detect_list_table_opportunities(None)
        self.assertEqual(result['score'], 100.0)

    def test_whitespace_content(self):
        result = detect_list_table_opportunities('   \n\n  ')
        self.assertEqual(result['score'], 100.0)

    def test_comma_enumeration_detected(self):
        content = '프레임워크에는 React, Vue, Angular, Svelte, Next.js가 있습니다.'
        result = detect_list_table_opportunities(content)
        self.assertGreater(result['summary']['list_candidates'], 0)

    def test_ordered_enumeration_korean(self):
        content = '첫째 환경을 설정하고, 둘째 코드를 작성하고, 셋째 테스트합니다.'
        result = detect_list_table_opportunities(content)
        self.assertGreater(result['summary']['list_candidates'], 0)

    def test_ordered_enumeration_english(self):
        content = 'First install the package. Second configure it. Third run tests.'
        result = detect_list_table_opportunities(content)
        self.assertGreater(result['summary']['list_candidates'], 0)

    def test_numbered_inline_pattern(self):
        content = '1) 환경 설정, 2) 코드 작성, 3) 테스트 실행을 순서대로 합니다.'
        result = detect_list_table_opportunities(content)
        self.assertGreater(result['summary']['list_candidates'], 0)

    def test_comparison_vs_pattern(self):
        content = 'React vs Vue: 어떤 프레임워크가 더 나을까요.'
        result = detect_list_table_opportunities(content)
        self.assertGreater(result['summary']['table_candidates'], 0)

    def test_comparison_korean_pattern(self):
        content = 'React는 가상 DOM을 사용하는 인 반면 Vue는 반응형 시스템을 사용합니다.'
        result = detect_list_table_opportunities(content)
        self.assertGreater(result['summary']['table_candidates'], 0)

    def test_comparison_english_pattern(self):
        content = 'React is component-based whereas Vue uses a template system.'
        result = detect_list_table_opportunities(content)
        self.assertGreater(result['summary']['table_candidates'], 0)

    def test_long_paragraph_detected(self):
        content = '가' * 250
        result = detect_list_table_opportunities(content)
        self.assertGreater(result['summary']['long_paragraphs'], 0)

    def test_short_paragraph_not_detected(self):
        content = '짧은 문단입니다.'
        result = detect_list_table_opportunities(content)
        self.assertEqual(result['summary']['total_opportunities'], 0)

    def test_multiple_sections(self):
        content = """## 프레임워크 비교
React vs Vue: 인기 있는 프론트엔드 프레임워크입니다.

## 설치 방법
첫째 npm을 설치하고, 둘째 패키지를 추가하고, 셋째 설정합니다.
"""
        result = detect_list_table_opportunities(content)
        self.assertGreater(result['summary']['total_opportunities'], 0)

    def test_score_decreases_with_opportunities(self):
        content = """React, Vue, Angular, Svelte, Next.js가 있습니다.

React vs Vue: 성능 비교입니다.
"""
        result = detect_list_table_opportunities(content)
        self.assertLess(result['score'], 100.0)

    def test_suggestions_for_list_candidates(self):
        content = '항목은 React, Vue, Angular, Svelte, Ember가 있습니다.'
        result = detect_list_table_opportunities(content)
        has_list_suggestion = any('목록' in s for s in result['suggestions'])
        self.assertTrue(has_list_suggestion)

    def test_suggestions_for_table_candidates(self):
        content = 'React vs Vue: 어떤 것이 나을까요.'
        result = detect_list_table_opportunities(content)
        has_table_suggestion = any('표' in s for s in result['suggestions'])
        self.assertTrue(has_table_suggestion)

    def test_no_opportunities_suggestion(self):
        content = '짧은 설명입니다.'
        result = detect_list_table_opportunities(content)
        if result['suggestions']:
            self.assertTrue(any('양호' in s for s in result['suggestions']))

    def test_return_structure(self):
        content = 'React, Vue, Angular, Svelte를 비교합니다.'
        result = detect_list_table_opportunities(content)
        self.assertIn('opportunities', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_opportunities', result['summary'])
        self.assertIn('list_candidates', result['summary'])
        self.assertIn('table_candidates', result['summary'])
        self.assertIn('long_paragraphs', result['summary'])

    def test_opportunity_has_excerpt(self):
        content = 'React, Vue, Angular, Svelte, Next.js를 사용합니다.'
        result = detect_list_table_opportunities(content)
        if result['opportunities']:
            opp = result['opportunities'][0]
            self.assertIn('excerpt', opp)
            self.assertIn('type', opp)
            self.assertIn('reason', opp)
            self.assertIn('section', opp)


if __name__ == '__main__':
    unittest.main()
