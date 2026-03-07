"""Cliché Detector 서비스 테스트."""
import unittest
from services.cliche_detector_service import detect_cliches


class TestClicheDetector(unittest.TestCase):

    def test_empty_content(self):
        result = detect_cliches('')
        self.assertEqual(result['summary']['total_cliches'], 0)
        self.assertEqual(result['score'], 100.0)

    def test_none_content(self):
        result = detect_cliches(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_cliches(self):
        content = '데이터 분석 결과를 기반으로 전략을 수립했습니다. 구체적인 실행 계획을 세웠습니다.'
        result = detect_cliches(content)
        self.assertEqual(result['summary']['total_cliches'], 0)
        self.assertEqual(result['summary']['level'], 'clean')

    def test_korean_opening_cliche(self):
        content = '오늘날 현대 사회에서 기술은 필수입니다.'
        result = detect_cliches(content)
        self.assertGreater(result['summary']['total_cliches'], 0)

    def test_korean_filler_cliche(self):
        content = '이 기술은 눈부신 성장을 이루었습니다. 불가분의 관계에 있습니다.'
        result = detect_cliches(content)
        self.assertGreater(result['summary']['total_cliches'], 0)

    def test_korean_closing_cliche(self):
        content = '모두 함께 노력하여 더 나은 미래를 만들어 갑시다.'
        result = detect_cliches(content)
        self.assertGreater(result['summary']['total_cliches'], 0)

    def test_english_cliche(self):
        content = 'We need to think outside the box. This is a game-changer for the industry.'
        result = detect_cliches(content)
        self.assertGreater(result['summary']['total_cliches'], 0)

    def test_multiple_cliches(self):
        content = ('오늘날 현대 사회에서 급변하는 시대에 맞추어 '
                   '눈부신 성장을 이루었습니다. '
                   '모두 함께 노력하여 더 나은 미래를 만듭시다.')
        result = detect_cliches(content)
        self.assertGreaterEqual(result['summary']['total_cliches'], 3)
        self.assertIn(result['summary']['level'], ('moderate', 'high'))

    def test_level_clean(self):
        content = '프로젝트 일정은 다음과 같습니다. 3월에 착수하고 6월에 완료합니다.'
        result = detect_cliches(content)
        self.assertEqual(result['summary']['level'], 'clean')

    def test_score_decreases_with_cliches(self):
        clean = '구체적인 데이터를 기반으로 분석했습니다.'
        dirty = '오늘날 현대 사회에서 급변하는 시대에 눈부신 성장을 이루었습니다.'
        clean_result = detect_cliches(clean)
        dirty_result = detect_cliches(dirty)
        self.assertGreater(clean_result['score'], dirty_result['score'])

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = detect_cliches(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인입니다.'
        result = detect_cliches(content)
        self.assertIn('cliches', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_cliches', result['summary'])
        self.assertIn('categories', result['summary'])
        self.assertIn('level', result['summary'])

    def test_cliche_structure(self):
        content = '오늘날 현대 사회에서 기술이 중요합니다.'
        result = detect_cliches(content)
        for c in result['cliches']:
            self.assertIn('text', c)
            self.assertIn('category', c)
            self.assertIn('language', c)
            self.assertIn('count', c)

    def test_suggestions_for_high(self):
        content = ('오늘날 현대 사회에서 급변하는 시대를 맞이하여 '
                   '눈부신 성장을 거듭 강조하며 '
                   '모두 함께 노력합니다.')
        result = detect_cliches(content)
        self.assertGreater(len(result['suggestions']), 0)


if __name__ == '__main__':
    unittest.main()
