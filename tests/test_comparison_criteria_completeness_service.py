"""Comparison Criteria Completeness Checker 서비스 테스트."""
import unittest
from services.comparison_criteria_completeness_service import check_comparison_criteria_completeness


class TestComparisonCriteriaCompleteness(unittest.TestCase):

    def test_empty_content(self):
        result = check_comparison_criteria_completeness('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = check_comparison_criteria_completeness(None)
        self.assertEqual(result['score'], 100.0)

    def test_non_comparison_content(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다.'
        result = check_comparison_criteria_completeness(content)
        self.assertFalse(result['summary']['is_comparison_content'])

    def test_comparison_detected(self):
        content = ('A vs B 비교 리뷰입니다. '
                   '두 제품을 직접 사용해 보았습니다.')
        result = check_comparison_criteria_completeness(content)
        self.assertTrue(result['summary']['is_comparison_content'])

    def test_explicit_criteria(self):
        content = ('A vs B 비교입니다. '
                   '평가 기준: 성능, 가격, 사용성. '
                   '각 항목별로 점수를 매겼습니다.')
        result = check_comparison_criteria_completeness(content)
        self.assertIn('explicit_criteria', result['summary']['criteria_found'])

    def test_rating_system(self):
        content = ('A vs B 비교 리뷰입니다. '
                   '성능: 8/10점. 가격: 7/10점. '
                   '디자인: 9점 만점에 8점.')
        result = check_comparison_criteria_completeness(content)
        self.assertIn('rating_system', result['summary']['criteria_found'])

    def test_structured_comparison(self):
        content = ('A vs B 비교입니다.\n'
                   '| 항목 | A | B |\n'
                   '| 성능 | 좋음 | 보통 |\n'
                   '| 가격 | 비쌈 | 저렴 |\n')
        result = check_comparison_criteria_completeness(content)
        self.assertIn('structured_comparison', result['summary']['criteria_found'])

    def test_methodology(self):
        content = ('A vs B 비교입니다. '
                   '테스트 방법: 실제 사용 환경에서 1주간 테스트했습니다.')
        result = check_comparison_criteria_completeness(content)
        self.assertIn('methodology', result['summary']['criteria_found'])

    def test_comprehensive_level(self):
        content = ('A vs B 비교 리뷰입니다.\n'
                   '평가 기준: 성능, 가격, 사용성, 디자인.\n'
                   '테스트 방법: 실제 사용 환경에서 직접 테스트했습니다.\n'
                   '| 항목 | A | B |\n| 성능 | 좋음 | 보통 |\n'
                   '성능: 8/10점. 가격: 7/10점.\n'
                   '중요도: 성능 > 가격 > 디자인.')
        result = check_comparison_criteria_completeness(content)
        self.assertIn(result['summary']['level'], ('comprehensive', 'good'))

    def test_missing_level(self):
        content = 'A vs B 비교입니다. A가 더 좋은 것 같습니다.'
        result = check_comparison_criteria_completeness(content)
        self.assertIn(result['summary']['level'], ('missing', 'minimal'))

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = check_comparison_criteria_completeness(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = 'A vs B 비교입니다.'
        result = check_comparison_criteria_completeness(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('criteria_details', result)
        self.assertIn('suggestions', result)
        self.assertIn('is_comparison_content', result['summary'])
        self.assertIn('criteria_categories', result['summary'])
        self.assertIn('criteria_found', result['summary'])
        self.assertIn('completeness_ratio', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_incomplete(self):
        content = 'A vs B 비교입니다. 둘 다 좋습니다.'
        result = check_comparison_criteria_completeness(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_english_comparison(self):
        content = ('Product A vs Product B comparison review. '
                   'We benchmark both products under the same test setup.')
        result = check_comparison_criteria_completeness(content)
        self.assertTrue(result['summary']['is_comparison_content'])

    def test_pros_cons_detection(self):
        content = '이 제품의 장단점을 분석합니다. 장점은 빠르고 단점은 비쌉니다.'
        result = check_comparison_criteria_completeness(content)
        self.assertTrue(result['summary']['is_comparison_content'])


if __name__ == '__main__':
    unittest.main()
