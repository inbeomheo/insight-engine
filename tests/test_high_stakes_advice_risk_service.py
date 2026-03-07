"""High-Stakes Advice Risk Detector 서비스 테스트."""
import unittest
from services.high_stakes_advice_risk_service import detect_high_stakes_advice_risk


class TestHighStakesAdviceRisk(unittest.TestCase):

    def test_empty_content(self):
        result = detect_high_stakes_advice_risk('')
        self.assertEqual(result['score'], 100.0)
        self.assertFalse(result['summary']['is_ymyl'])

    def test_none_content(self):
        result = detect_high_stakes_advice_risk(None)
        self.assertEqual(result['score'], 100.0)

    def test_non_ymyl_content(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다. 맛있는 점심을 먹었습니다.'
        result = detect_high_stakes_advice_risk(content)
        self.assertFalse(result['summary']['is_ymyl'])
        self.assertEqual(result['summary']['risk_level'], 'none')

    def test_medical_without_disclaimer(self):
        content = ('두통 증상이 있을 때 이 약물을 복용하세요. '
                   '부작용으로 어지러움이 있을 수 있습니다. '
                   '치료 효과가 뛰어납니다.')
        result = detect_high_stakes_advice_risk(content)
        self.assertTrue(result['summary']['is_ymyl'])
        self.assertEqual(result['summary']['risk_level'], 'high')

    def test_medical_with_disclaimer(self):
        content = ('두통 증상이 있을 때 참고할 수 있는 정보입니다. '
                   '이 약물의 부작용에 대해 알아봅니다. '
                   '본 글은 참고용이며, 전문가 상담을 권장합니다. '
                   '의사와 상의한 후 복용하세요.')
        result = detect_high_stakes_advice_risk(content)
        self.assertTrue(result['summary']['has_disclaimer'])

    def test_financial_content(self):
        content = ('주식 투자 방법을 알아봅니다. '
                   '이 펀드의 수익률은 높습니다. '
                   '대출 금리를 비교해보겠습니다.')
        result = detect_high_stakes_advice_risk(content)
        self.assertTrue(result['summary']['is_ymyl'])
        ymyl_domains = [d['domain'] for d in result['summary']['ymyl_domains']]
        self.assertIn('financial', ymyl_domains)

    def test_legal_content(self):
        content = ('소송 절차에 대해 알아봅니다. '
                   '계약서 작성 시 주의할 법률 조항입니다. '
                   '변호사 선임 없이 법원에 가는 방법.')
        result = detect_high_stakes_advice_risk(content)
        self.assertTrue(result['summary']['is_ymyl'])

    def test_with_authority(self):
        content = ('건강 관리에 대한 정보입니다. 영양제 복용 가이드입니다. '
                   '이 글은 홍길동 의사가 감수하였습니다. '
                   '본 콘텐츠는 참고용 자료입니다.')
        result = detect_high_stakes_advice_risk(content)
        self.assertTrue(result['summary']['has_authority'])

    def test_english_ymyl(self):
        content = ('This medication has side effects you should know about. '
                   'The treatment is effective for most patients. '
                   'Consult your doctor before taking any supplements. '
                   'This is for informational purposes only.')
        result = detect_high_stakes_advice_risk(content)
        self.assertTrue(result['summary']['is_ymyl'])
        self.assertTrue(result['summary']['has_disclaimer'])

    def test_low_risk(self):
        content = ('건강 관리 팁입니다. 영양제에 대해 알아봅니다. '
                   '감수: 김박사 전문의. '
                   '본 글은 참고용이며 전문가 상담을 받으세요.')
        result = detect_high_stakes_advice_risk(content)
        self.assertEqual(result['summary']['risk_level'], 'low')

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = detect_high_stakes_advice_risk(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = detect_high_stakes_advice_risk(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('risk_spans', result)
        self.assertIn('missing_safety_signals', result)
        self.assertIn('suggestions', result)
        self.assertIn('is_ymyl', result['summary'])
        self.assertIn('has_disclaimer', result['summary'])
        self.assertIn('has_authority', result['summary'])
        self.assertIn('risk_level', result['summary'])

    def test_suggestions_for_high_risk(self):
        content = ('투자 상품을 추천합니다. 주식 매수 타이밍입니다. '
                   '이 펀드에 투자하면 수익률이 높습니다.')
        result = detect_high_stakes_advice_risk(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_safety_domain(self):
        content = ('전기 작업 시 안전에 주의하세요. '
                   '감전 위험이 있으며 사고 예방이 중요합니다.')
        result = detect_high_stakes_advice_risk(content)
        self.assertTrue(result['summary']['is_ymyl'])


if __name__ == '__main__':
    unittest.main()
