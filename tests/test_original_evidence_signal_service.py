"""Original Evidence Signal Analyzer 서비스 테스트."""
import unittest
from services.analysis.original_evidence_signal_service import analyze_original_evidence


class TestOriginalEvidence(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_original_evidence('')
        self.assertEqual(result['score'], 50.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = analyze_original_evidence(None)
        self.assertEqual(result['score'], 50.0)

    def test_no_evidence(self):
        content = '이 제품은 좋습니다. 추천합니다. 가격도 합리적입니다.'
        result = analyze_original_evidence(content)
        self.assertEqual(result['summary']['level'], 'missing')

    def test_direct_experience(self):
        content = '직접 사용해 본 결과, 성능이 매우 우수했습니다.'
        result = analyze_original_evidence(content)
        self.assertIn('direct_experience', result['summary']['signals_found'])

    def test_original_data(self):
        content = '자체 테스트 결과를 바탕으로 분석했습니다. 우리 데이터에 따르면 효과적입니다.'
        result = analyze_original_evidence(content)
        self.assertIn('original_data', result['summary']['signals_found'])

    def test_visual_evidence(self):
        content = '아래 스크린샷에서 확인할 수 있습니다. ![결과](result.png)'
        result = analyze_original_evidence(content)
        self.assertIn('visual_evidence', result['summary']['signals_found'])

    def test_specific_metrics(self):
        content = '응답 시간이 평균 120ms로 매우 빨랐습니다. 100회 테스트를 진행했습니다.'
        result = analyze_original_evidence(content)
        self.assertIn('specific_metrics', result['summary']['signals_found'])

    def test_test_environment(self):
        content = '테스트 환경: Ubuntu 22.04, CPU: i7-12700, RAM: 32GB.'
        result = analyze_original_evidence(content)
        self.assertIn('test_environment', result['summary']['signals_found'])

    def test_strong_level(self):
        content = ('직접 테스트한 결과입니다. '
                   '자체 데이터를 바탕으로 분석했습니다. '
                   '아래 스크린샷을 참고하세요. '
                   '응답 시간 평균 50ms로 빨랐습니다. '
                   '테스트 환경: macOS 14.')
        result = analyze_original_evidence(content)
        self.assertIn(result['summary']['level'], ('strong', 'good'))

    def test_english_evidence(self):
        content = ('I tested this library in our production environment. '
                   'Our data shows 40% improvement. '
                   'Latency of 15ms was measured.')
        result = analyze_original_evidence(content)
        self.assertGreater(result['summary']['evidence_categories'], 0)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = analyze_original_evidence(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = analyze_original_evidence(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('evidence_signals', result)
        self.assertIn('suggestions', result)
        self.assertIn('evidence_categories', result['summary'])
        self.assertIn('signals_found', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_missing(self):
        content = '이 제품은 좋습니다. 추천합니다.'
        result = analyze_original_evidence(content)
        self.assertGreater(len(result['suggestions']), 0)


if __name__ == '__main__':
    unittest.main()
