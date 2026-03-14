"""Absolute Claim Risk Detector 서비스 테스트."""
import unittest
from services.analysis.absolute_claim_risk_service import detect_absolute_claim_risk


class TestAbsoluteClaimRisk(unittest.TestCase):

    def test_empty_content(self):
        result = detect_absolute_claim_risk('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = detect_absolute_claim_risk(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_absolute_terms(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다. 맛있는 점심을 먹었습니다.'
        result = detect_absolute_claim_risk(content)
        self.assertEqual(result['summary']['absolute_count'], 0)
        self.assertEqual(result['summary']['level'], 'safe')

    def test_unqualified_absolute_ko(self):
        content = '이 방법은 항상 효과적입니다. 절대 실패하지 않습니다.'
        result = detect_absolute_claim_risk(content)
        self.assertGreater(result['summary']['unqualified_count'], 0)

    def test_qualified_absolute_ko(self):
        content = '일반적으로 이 방법은 항상 효과적이라고 알려져 있습니다.'
        result = detect_absolute_claim_risk(content)
        self.assertGreater(result['summary']['qualified_count'], 0)

    def test_unqualified_absolute_en(self):
        content = ('This method always works perfectly. '
                   'It will never fail under any circumstances. '
                   'Everyone should use this approach.')
        result = detect_absolute_claim_risk(content)
        self.assertGreater(result['summary']['unqualified_count'], 0)

    def test_qualified_absolute_en(self):
        content = 'This method usually always works well in most cases.'
        result = detect_absolute_claim_risk(content)
        self.assertGreater(result['summary']['qualified_count'], 0)

    def test_high_risk(self):
        content = ('이것은 최고의 제품입니다. '
                   '100% 보장합니다. '
                   '절대 후회하지 않을 것입니다. '
                   '모든 사람에게 완벽합니다.')
        result = detect_absolute_claim_risk(content)
        self.assertEqual(result['summary']['level'], 'high')
        self.assertLessEqual(result['score'], 30.0)

    def test_safe_level(self):
        content = ('일반적으로 좋은 결과를 얻을 수 있습니다. '
                   '대부분의 경우 효과적입니다. '
                   '상황에 따라 다를 수 있습니다.')
        result = detect_absolute_claim_risk(content)
        self.assertEqual(result['summary']['level'], 'safe')
        self.assertEqual(result['score'], 100.0)

    def test_risky_claims_list(self):
        content = '이 제품은 최고의 선택입니다. 절대 실패하지 않습니다.'
        result = detect_absolute_claim_risk(content)
        self.assertGreater(len(result['risky_claims']), 0)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = detect_absolute_claim_risk(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = detect_absolute_claim_risk(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('risky_claims', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sentences', result['summary'])
        self.assertIn('absolute_count', result['summary'])
        self.assertIn('qualified_count', result['summary'])
        self.assertIn('unqualified_count', result['summary'])
        self.assertIn('risk_ratio', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_risky(self):
        content = '이 방법은 항상 최고입니다. 절대로 다른 것을 쓰지 마세요.'
        result = detect_absolute_claim_risk(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_mixed_qualified_unqualified(self):
        content = ('일반적으로 항상 좋은 결과를 얻습니다. '
                   '이것은 절대 실패하지 않습니다. '
                   '무조건 써야 합니다.')
        result = detect_absolute_claim_risk(content)
        self.assertGreater(result['summary']['qualified_count'], 0)
        self.assertGreater(result['summary']['absolute_count'],
                           result['summary']['qualified_count'])


if __name__ == '__main__':
    unittest.main()
