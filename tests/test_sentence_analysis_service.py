"""sentence_analysis_service 단위 테스트 — 주요 public 분석 함수 검증"""
import unittest

from services.analysis.sentence_analysis_service import (
    analyze_variety,
    analyze_connector_variety,
    analyze_sentence_rhythm,
    analyze_sentence_ending_variety,
    score_sentence_complexity,
)


class TestAnalyzeVariety(unittest.TestCase):
    """analyze_variety: 문장 다양성 분석"""

    def test_empty_content_returns_empty(self):
        result = analyze_variety("")
        self.assertEqual(result['variety_score'], 0)
        self.assertIn('콘텐츠가 비어 있습니다.', result['suggestions'])

    def test_normal_content(self):
        content = (
            "인공지능은 빠르게 발전하고 있습니다. "
            "많은 기업이 AI를 도입하고 있습니다. "
            "그러나 윤리적 문제도 함께 대두되고 있습니다. "
            "전문가들은 규제가 필요하다고 말합니다. "
            "향후 10년 안에 큰 변화가 있을 것입니다."
        )
        result = analyze_variety(content)
        self.assertIn('variety_score', result)
        self.assertIsInstance(result['variety_score'], int)
        self.assertGreater(result['stats']['count'], 0)
        self.assertIn('sentences', result)

    def test_single_sentence(self):
        result = analyze_variety("이것은 하나의 문장입니다.")
        self.assertGreaterEqual(result['variety_score'], 0)


class TestAnalyzeConnectorVariety(unittest.TestCase):
    """analyze_connector_variety: 연결어 다양성"""

    def test_empty_content(self):
        result = analyze_connector_variety("")
        self.assertEqual(result['summary']['connector_count'], 0)

    def test_with_connectors(self):
        content = (
            "그리고 첫 번째 주제를 살펴봅니다. "
            "그러나 이견도 있습니다. "
            "따라서 신중한 접근이 필요합니다. "
            "예를 들어 유럽의 사례가 있습니다. "
            "결론적으로 균형이 중요합니다."
        )
        result = analyze_connector_variety(content)
        self.assertGreater(result['summary']['connector_count'], 0)
        self.assertIn('score', result)

    def test_no_connectors(self):
        content = "이것은 문장입니다. 또 다른 문장입니다."
        result = analyze_connector_variety(content)
        self.assertEqual(result['summary']['connector_count'], 0)


class TestAnalyzeSentenceRhythm(unittest.TestCase):
    """analyze_sentence_rhythm: 문장 길이 리듬"""

    def test_empty(self):
        result = analyze_sentence_rhythm("")
        self.assertIn('콘텐츠가 비어 있습니다.', result['suggestions'])

    def test_varied_lengths(self):
        content = (
            "짧다. "
            "이것은 중간 길이의 문장으로 적당한 정보를 담고 있습니다. "
            "매우 긴 문장은 독자에게 피로감을 줄 수 있으므로 적절한 길이로 조절하는 것이 좋습니다."
        )
        result = analyze_sentence_rhythm(content)
        self.assertIn('score', result)
        self.assertIn('rhythm_quality', result['summary'])


class TestAnalyzeSentenceEndingVariety(unittest.TestCase):
    """analyze_sentence_ending_variety: 종결어미 다양성"""

    def test_empty(self):
        result = analyze_sentence_ending_variety("")
        self.assertEqual(result['summary']['total_sentences'], 0)

    def test_korean_endings(self):
        content = (
            "AI는 발전합니다. "
            "새로운 기술이 있습니다. "
            "어떻게 활용할까요? "
            "직접 확인해 보세요!"
        )
        result = analyze_sentence_ending_variety(content)
        self.assertGreater(result['summary']['unique_endings'], 1)


class TestScoreSentenceComplexity(unittest.TestCase):
    """score_sentence_complexity: 문장 복잡도"""

    def test_empty(self):
        result = score_sentence_complexity("")
        self.assertIn('콘텐츠가 비어 있습니다.', result['suggestions'])

    def test_simple_sentences(self):
        content = "간단한 문장. 짧은 텍스트. 명확합니다."
        result = score_sentence_complexity(content)
        self.assertIn('level', result['summary'])

    def test_complex_sentence(self):
        content = (
            "AI가 발전하고, 데이터가 축적되며, 알고리즘이 개선되면서, "
            "이 모든 요소(기술, 인프라, 인재)가 결합되어 "
            "혁명적인 변화가 일어나는데, 그 과정에서 "
            "다양한 윤리적 문제가 발생하지만 해결할 수 있습니다."
        )
        result = score_sentence_complexity(content)
        self.assertIn('sentences', result)
        if result['sentences']:
            self.assertIn('complexity', result['sentences'][0])


if __name__ == '__main__':
    unittest.main()
