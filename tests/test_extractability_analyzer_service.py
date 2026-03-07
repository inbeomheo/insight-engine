"""Context-Free Extractability Analyzer 서비스 테스트."""
import unittest
from services.extractability_analyzer_service import analyze_extractability


class TestExtractabilityAnalyzer(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_extractability('')
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = analyze_extractability(None)
        self.assertEqual(result['score'], 0.0)

    def test_extractable_definitions(self):
        content = ('Python은 범용 프로그래밍 언어로 간결한 문법이 특징입니다. '
                   'Django는 Python 기반의 웹 프레임워크입니다. '
                   'Flask는 경량 웹 프레임워크로 마이크로서비스에 적합합니다.')
        result = analyze_extractability(content)
        self.assertGreater(result['summary']['extractable_count'], 0)

    def test_context_dependent_sentences(self):
        content = ('이것은 매우 중요합니다. 위에서 말한 것처럼 진행합니다. '
                   '그 결과 성공했습니다. 이러한 방법으로 해결합니다.')
        result = analyze_extractability(content)
        self.assertGreater(result['summary']['dependent_count'], 0)

    def test_mixed_content(self):
        content = ('Python은 1991년에 만들어진 프로그래밍 언어입니다. '
                   '이것은 매우 유용합니다. '
                   'Git은 분산 버전 관리 시스템입니다. '
                   '위에서 설명한 대로 설정합니다.')
        result = analyze_extractability(content)
        self.assertGreater(result['summary']['extractable_count'], 0)
        self.assertGreater(result['summary']['dependent_count'], 0)

    def test_numeric_facts(self):
        content = ('메모리 사용량은 512MB입니다. 응답 시간은 200ms 이내입니다. '
                   '사용자의 85%가 만족합니다. 처리 속도가 3배 향상되었습니다.')
        result = analyze_extractability(content)
        self.assertGreater(result['summary']['extractable_count'], 0)

    def test_english_definitions(self):
        content = ('Docker is a platform for containerized applications. '
                   'Kubernetes refers to an orchestration system for containers. '
                   'This makes it very useful for deployment.')
        result = analyze_extractability(content)
        self.assertGreater(result['summary']['extractable_count'], 0)

    def test_extractable_ratio(self):
        content = ('REST API는 웹 서비스 아키텍처 스타일입니다. '
                   'JSON은 경량 데이터 교환 형식입니다. '
                   'HTTP 상태 코드 200은 성공을 의미합니다.')
        result = analyze_extractability(content)
        self.assertGreater(result['summary']['extractable_ratio'], 0.0)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다. 다양한 내용을 포함합니다.'
        result = analyze_extractability(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다. 여러 문장이 포함됩니다.'
        result = analyze_extractability(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('flagged_spans', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sentences', result['summary'])
        self.assertIn('extractable_count', result['summary'])
        self.assertIn('dependent_count', result['summary'])
        self.assertIn('extractable_ratio', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_exist(self):
        content = ('이것은 중요합니다. 그 결과가 좋습니다. '
                   '위에서 언급한 내용입니다.')
        result = analyze_extractability(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_flagged_spans(self):
        content = ('이것은 테스트용 문맥 의존 문장입니다. '
                   '위에서 설명한 방법을 사용합니다. '
                   'Python은 프로그래밍 언어입니다.')
        result = analyze_extractability(content)
        self.assertIsInstance(result['flagged_spans'], list)


if __name__ == '__main__':
    unittest.main()
