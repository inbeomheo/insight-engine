"""Quantifier Specificity Analyzer 서비스 테스트."""
import unittest
from services.analysis.quantifier_specificity_service import analyze_quantifier_specificity


class TestQuantifierSpecificity(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_quantifier_specificity('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = analyze_quantifier_specificity(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_quantifiers(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다.'
        result = analyze_quantifier_specificity(content)
        self.assertEqual(result['summary']['vague_count'], 0)

    def test_vague_ko(self):
        content = '많은 사용자가 이 기능을 사용합니다. 대부분의 경우 효과적입니다.'
        result = analyze_quantifier_specificity(content)
        self.assertGreater(result['summary']['vague_count'], 0)
        self.assertGreater(len(result['vague_quantifiers']), 0)

    def test_vague_en(self):
        content = 'Many users love this feature. Several companies adopted it.'
        result = analyze_quantifier_specificity(content)
        self.assertGreater(result['summary']['vague_count'], 0)

    def test_specific_numbers(self):
        content = '73%의 사용자가 이 기능을 사용합니다. 5가지 방법이 있습니다.'
        result = analyze_quantifier_specificity(content)
        self.assertGreater(result['summary']['specific_count'], 0)

    def test_specific_level(self):
        content = ('전체의 85%가 참여했습니다. '
                   '3가지 옵션이 있습니다. '
                   '매출이 2배 증가했습니다.')
        result = analyze_quantifier_specificity(content)
        self.assertEqual(result['summary']['level'], 'specific')
        self.assertEqual(result['score'], 100.0)

    def test_vague_level(self):
        content = ('많은 사람들이 참여했습니다. '
                   '대부분의 기업이 도입했습니다. '
                   '상당한 효과가 있었습니다. '
                   '여러 방법이 있습니다.')
        result = analyze_quantifier_specificity(content)
        self.assertEqual(result['summary']['level'], 'vague')
        self.assertLessEqual(result['score'], 30.0)

    def test_mixed_vague_specific(self):
        content = ('많은 사용자가 있지만 정확히 73%입니다. '
                   '대부분 성공합니다.')
        result = analyze_quantifier_specificity(content)
        self.assertGreater(result['summary']['vague_count'], 0)
        self.assertGreater(result['summary']['specific_count'], 0)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = analyze_quantifier_specificity(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = analyze_quantifier_specificity(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('vague_quantifiers', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sentences', result['summary'])
        self.assertIn('vague_count', result['summary'])
        self.assertIn('specific_count', result['summary'])
        self.assertIn('specificity_ratio', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_vague(self):
        content = '많은 기업이 도입했습니다. 일부 사용자만 사용합니다.'
        result = analyze_quantifier_specificity(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_vague_with_specific_in_same_sentence(self):
        content = '많은, 약 200명의 사용자가 참여했습니다.'
        result = analyze_quantifier_specificity(content)
        # 같은 문장에 수치가 있으면 vague_quantifiers에 포함되지 않음
        self.assertEqual(len(result['vague_quantifiers']), 0)

    def test_specificity_ratio(self):
        content = ('약 50%가 참여했습니다. '
                   '많은 사람이 옵니다.')
        result = analyze_quantifier_specificity(content)
        self.assertGreater(result['summary']['specificity_ratio'], 0.0)
        self.assertLess(result['summary']['specificity_ratio'], 100.0)


if __name__ == '__main__':
    unittest.main()
