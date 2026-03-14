"""Numeric & Unit Consistency Checker 서비스 테스트."""
import unittest
from services.analysis.numeric_unit_consistency_service import check_numeric_unit_consistency


class TestNumericUnitConsistency(unittest.TestCase):

    def test_empty_content(self):
        result = check_numeric_unit_consistency('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = check_numeric_unit_consistency(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_numeric(self):
        content = '일반적인 텍스트입니다. 숫자가 없습니다.'
        result = check_numeric_unit_consistency(content)
        self.assertEqual(result['summary']['categories_checked'], 0)

    def test_consistent_currency(self):
        content = '가격은 $10입니다. 할인 후 $8입니다.'
        result = check_numeric_unit_consistency(content)
        self.assertEqual(result['summary']['inconsistent_count'], 0)

    def test_inconsistent_currency(self):
        content = '가격은 $10입니다. 국내에서는 15000원입니다.'
        result = check_numeric_unit_consistency(content)
        currency_issues = [i for i in result['consistency_issues']
                           if i['category'] == 'currency']
        self.assertGreater(len(currency_issues), 0)

    def test_consistent_percent(self):
        content = '성공률은 85%입니다. 실패율은 15%입니다.'
        result = check_numeric_unit_consistency(content)
        percent_issues = [i for i in result['consistency_issues']
                          if i['category'] == 'percent']
        self.assertEqual(len(percent_issues), 0)

    def test_inconsistent_percent(self):
        content = '성공률은 85%입니다. 실패율은 15퍼센트입니다.'
        result = check_numeric_unit_consistency(content)
        percent_issues = [i for i in result['consistency_issues']
                          if i['category'] == 'percent']
        self.assertGreater(len(percent_issues), 0)

    def test_inconsistent_date(self):
        content = '시작일은 2025-01-15이고, 종료일은 2025.03.20입니다.'
        result = check_numeric_unit_consistency(content)
        date_issues = [i for i in result['consistency_issues']
                       if i['category'] == 'date']
        self.assertGreater(len(date_issues), 0)

    def test_consistent_date(self):
        content = '시작일은 2025-01-15이고, 종료일은 2025-03-20입니다.'
        result = check_numeric_unit_consistency(content)
        date_issues = [i for i in result['consistency_issues']
                       if i['category'] == 'date']
        self.assertEqual(len(date_issues), 0)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = check_numeric_unit_consistency(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = check_numeric_unit_consistency(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('consistency_issues', result)
        self.assertIn('suggestions', result)
        self.assertIn('categories_checked', result['summary'])
        self.assertIn('inconsistent_count', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_inconsistency(self):
        content = '가격은 $10입니다. 국내가는 15000원입니다.'
        result = check_numeric_unit_consistency(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_multiple_inconsistencies(self):
        content = ('가격은 $10이고 국내는 15000원입니다. '
                   '성공률은 85%이고 실패율은 15퍼센트입니다. '
                   '시작일 2025-01-15, 종료일 2025.03.20입니다.')
        result = check_numeric_unit_consistency(content)
        self.assertGreater(result['summary']['inconsistent_count'], 1)

    def test_consistent_level(self):
        content = '가격은 $10입니다. 할인가는 $8입니다. 배송비는 $2입니다.'
        result = check_numeric_unit_consistency(content)
        self.assertIn(result['summary']['level'], ('none', 'consistent'))


if __name__ == '__main__':
    unittest.main()
