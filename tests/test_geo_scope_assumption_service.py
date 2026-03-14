"""Geo Scope Assumption Detector 서비스 테스트."""
import unittest
from services.analysis.geo_scope_assumption_service import detect_geo_scope_assumptions


class TestGeoScopeAssumption(unittest.TestCase):

    def test_empty_content(self):
        result = detect_geo_scope_assumptions('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = detect_geo_scope_assumptions(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_geo_sensitive(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다.'
        result = detect_geo_scope_assumptions(content)
        self.assertEqual(len(result['summary']['geo_sensitive_found']), 0)

    def test_price_without_label(self):
        content = '이 서비스의 가격은 월 $29입니다. 연간 요금은 $299입니다.'
        result = detect_geo_scope_assumptions(content)
        self.assertIn('price', result['summary']['geo_sensitive_found'])
        self.assertFalse(result['summary']['has_geo_label'])

    def test_price_with_label(self):
        content = '한국 기준 가격은 월 29,000원입니다. 미국에서는 $29입니다.'
        result = detect_geo_scope_assumptions(content)
        self.assertTrue(result['summary']['has_geo_label'])

    def test_tax_sensitive(self):
        content = '부가세 10%가 별도 부과됩니다. 세금 공제를 받을 수 있습니다.'
        result = detect_geo_scope_assumptions(content)
        self.assertIn('tax', result['summary']['geo_sensitive_found'])

    def test_regulation_sensitive(self):
        content = '이 활동은 합법적이며 법률에 따라 허가가 필요합니다.'
        result = detect_geo_scope_assumptions(content)
        self.assertIn('regulation', result['summary']['geo_sensitive_found'])

    def test_shipping_sensitive(self):
        content = '무료 배송이 가능합니다. 배송비는 3,000원입니다.'
        result = detect_geo_scope_assumptions(content)
        self.assertIn('shipping', result['summary']['geo_sensitive_found'])

    def test_labeled_content(self):
        content = ('국내 기준으로 세금은 10%입니다. '
                   '한국에서의 배송비는 3,000원입니다. '
                   '해외 배송은 별도 문의하세요.')
        result = detect_geo_scope_assumptions(content)
        self.assertTrue(result['summary']['has_geo_label'])
        self.assertEqual(result['summary']['level'], 'labeled')

    def test_english_geo_sensitive(self):
        content = ('Shipping is free for all orders. '
                   'Sales tax will be applied at checkout.')
        result = detect_geo_scope_assumptions(content)
        self.assertGreater(len(result['summary']['geo_sensitive_found']), 0)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = detect_geo_scope_assumptions(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = detect_geo_scope_assumptions(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('geo_sensitive_terms', result)
        self.assertIn('unlabeled_scope_issues', result)
        self.assertIn('suggestions', result)
        self.assertIn('geo_sensitive_found', result['summary'])
        self.assertIn('has_geo_label', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_unlabeled(self):
        content = '가격은 월 $50이며 세율은 8%입니다.'
        result = detect_geo_scope_assumptions(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_global_label(self):
        content = '글로벌 서비스로 가격은 $29입니다. 국내에서도 이용 가능합니다.'
        result = detect_geo_scope_assumptions(content)
        self.assertTrue(result['summary']['has_geo_label'])


if __name__ == '__main__':
    unittest.main()
