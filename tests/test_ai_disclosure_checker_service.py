"""AI/Automation Disclosure Checker 서비스 테스트."""
import unittest
from services.quality.ai_disclosure_checker_service import check_ai_disclosure


class TestAIDisclosure(unittest.TestCase):

    def test_empty_content(self):
        result = check_ai_disclosure('')
        self.assertEqual(result['score'], 100.0)
        self.assertFalse(result['summary']['has_ai_markers'])

    def test_none_content(self):
        result = check_ai_disclosure(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_ai_markers(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다. 자연이 아름답습니다.'
        result = check_ai_disclosure(content)
        self.assertFalse(result['summary']['has_ai_markers'])
        self.assertEqual(result['score'], 100.0)

    def test_ai_marker_without_disclosure(self):
        content = ('이 글은 ChatGPT를 활용하여 작성했습니다. '
                   'AI 기반 분석 결과를 공유합니다.')
        result = check_ai_disclosure(content)
        self.assertTrue(result['summary']['has_ai_markers'])
        self.assertLess(result['score'], 100.0)

    def test_ai_marker_with_disclosure(self):
        content = ('본 글은 AI 활용하여 작성되었으며 편집 담당: 홍길동. '
                   'ChatGPT로 초안을 작성하고 사람이 검토했습니다.')
        result = check_ai_disclosure(content)
        self.assertTrue(result['summary']['disclosure_found'])
        self.assertTrue(result['summary']['human_review_noted'])

    def test_english_ai_markers(self):
        content = ('This article was AI-generated using GPT-4. '
                   'The content has been human-reviewed and verified.')
        result = check_ai_disclosure(content)
        self.assertTrue(result['summary']['has_ai_markers'])
        self.assertTrue(result['summary']['disclosure_found'])

    def test_automation_traces(self):
        content = ("As an AI language model, I cannot provide medical advice. "
                   "However, I can share general information about this topic.")
        result = check_ai_disclosure(content)
        self.assertGreater(result['summary']['automation_traces'], 0)

    def test_korean_automation_traces(self):
        content = ('요약하자면, 다음과 같습니다. '
                   '도움이 되었으면 좋겠습니다. 궁금한 점이 있으시면 질문해주세요.')
        result = check_ai_disclosure(content)
        self.assertGreater(result['summary']['automation_traces'], 0)

    def test_ai_without_human_review(self):
        content = ('본 콘텐츠는 AI 생성 콘텐츠입니다. '
                   'Gemini를 활용하여 자동 작성되었습니다.')
        result = check_ai_disclosure(content)
        self.assertTrue(result['summary']['has_ai_markers'])
        self.assertFalse(result['summary']['human_review_noted'])

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = check_ai_disclosure(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = check_ai_disclosure(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('ai_markers', result)
        self.assertIn('disclosure_markers', result)
        self.assertIn('automation_traces', result)
        self.assertIn('suggestions', result)
        self.assertIn('has_ai_markers', result['summary'])
        self.assertIn('disclosure_found', result['summary'])
        self.assertIn('automation_traces', result['summary'])
        self.assertIn('human_review_noted', result['summary'])

    def test_suggestions_for_missing_disclosure(self):
        content = 'AI 작성 콘텐츠입니다. GPT-4로 생성했습니다.'
        result = check_ai_disclosure(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_llm_keyword(self):
        content = 'LLM 기반으로 대규모 언어 모델을 활용한 분석입니다.'
        result = check_ai_disclosure(content)
        self.assertTrue(result['summary']['has_ai_markers'])

    def test_claude_mention(self):
        content = 'Claude를 사용하여 이 문서를 작성했습니다.'
        result = check_ai_disclosure(content)
        self.assertTrue(result['summary']['has_ai_markers'])


if __name__ == '__main__':
    unittest.main()
