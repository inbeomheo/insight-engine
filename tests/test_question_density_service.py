"""Question Density Analyzer 서비스 테스트."""
import unittest
from services.analysis.question_density_service import analyze_question_density


class TestQuestionDensityAnalyzer(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_question_density('')
        self.assertEqual(result['summary']['total_questions'], 0)
        self.assertEqual(result['score'], 50.0)

    def test_none_content(self):
        result = analyze_question_density(None)
        self.assertEqual(result['summary']['total_questions'], 0)

    def test_no_questions(self):
        content = '이것은 설명문입니다. 질문이 없습니다. 서술만 있습니다.'
        result = analyze_question_density(content)
        self.assertEqual(result['summary']['total_questions'], 0)
        self.assertEqual(result['score'], 40.0)

    def test_korean_question_mark(self):
        content = '왜 테스트가 중요할까요? 설명드리겠습니다. 테스트는 품질을 보장합니다.'
        result = analyze_question_density(content)
        self.assertGreater(result['summary']['total_questions'], 0)

    def test_english_question_mark(self):
        content = 'Why is testing important? Let me explain. Tests ensure quality.'
        result = analyze_question_density(content)
        self.assertGreater(result['summary']['total_questions'], 0)

    def test_korean_question_without_mark(self):
        content = '무엇을 해야 하는지 설명합니다. 어떻게 구현하는지 알아봅니다.'
        result = analyze_question_density(content)
        self.assertGreater(result['summary']['total_questions'], 0)

    def test_english_question_word(self):
        content = 'What makes this important. How to implement it. Regular sentence here.'
        result = analyze_question_density(content)
        self.assertGreater(result['summary']['total_questions'], 0)

    def test_high_density(self):
        content = '왜일까요? 어떻게 할까요? 무엇일까요? 언제일까요? 누가할까요?'
        result = analyze_question_density(content)
        self.assertGreater(result['summary']['question_density'], 50)

    def test_rhetorical_question(self):
        content = '정말 그럴까요? 네, 맞습니다. 확실합니다.'
        result = analyze_question_density(content)
        self.assertGreater(result['summary']['rhetorical_count'], 0)

    def test_section_analysis(self):
        content = """## 소개
왜 중요할까요? 설명합니다.

## 본론
본론 내용입니다. 서술형 텍스트입니다.
"""
        result = analyze_question_density(content)
        self.assertGreater(len(result['section_analysis']), 0)

    def test_optimal_density_score(self):
        # 적정 밀도 (5-15%)에서 높은 점수
        sentences = ['서술 문장입니다.'] * 8 + ['왜 그럴까요?']
        content = ' '.join(sentences)
        result = analyze_question_density(content)
        self.assertGreaterEqual(result['score'], 50.0)

    def test_suggestions_no_questions(self):
        content = '서술 문장입니다. 다른 서술 문장입니다.'
        result = analyze_question_density(content)
        self.assertTrue(any('질문이 없습니다' in s for s in result['suggestions']))

    def test_return_structure(self):
        content = '왜 테스트가 중요할까요? 설명합니다.'
        result = analyze_question_density(content)
        self.assertIn('questions', result)
        self.assertIn('section_analysis', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_questions', result['summary'])
        self.assertIn('question_density', result['summary'])


if __name__ == '__main__':
    unittest.main()
