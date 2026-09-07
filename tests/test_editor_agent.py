"""
EditorAgent 단위 테스트
"""
import json
import unittest
from unittest.mock import patch, MagicMock


class TestEditorAgent(unittest.TestCase):
    """services.agents.editor_agent.EditorAgent 테스트"""

    def _mock_completion(self, content: str):
        mock = MagicMock()
        mock.choices[0].message.content = content
        return mock

    def _make_agent(self):
        from services.agents.editor_agent import EditorAgent
        return EditorAgent(model='gemini/gemini-3-flash-preview')

    # --- 초기화 ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    def test_init_properties(self, _):
        agent = self._make_agent()
        self.assertEqual(agent.name, 'editor')
        self.assertEqual(agent.role, '콘텐츠 교정 및 품질 검증')

    # --- execute: 정상 ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    @patch('litellm.completion')
    def test_execute_returns_edited_content(self, mock_llm, _):
        edited_md = '# 교정된 제목\n\n교정된 본문입니다.'
        quality_json = json.dumps({
            "grade": "A", "readability": 9, "accuracy": 9,
            "issues": [], "summary": "우수"
        })
        mock_llm.side_effect = [
            self._mock_completion(edited_md),
            self._mock_completion(quality_json),
        ]

        agent = self._make_agent()
        result = agent.execute({'draft': '# 원본\n본문', 'summary': '요약'})

        self.assertEqual(result['agent'], 'editor')
        self.assertIn('교정된 제목', result['edited_content'])
        self.assertEqual(result['title'], '교정된 제목')
        self.assertEqual(result['quality']['grade'], 'A')

    # --- execute: 빈 초안 ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    def test_execute_empty_draft(self, _):
        agent = self._make_agent()
        result = agent.execute({'draft': ''})

        self.assertEqual(result['edited_content'], '')
        self.assertEqual(result['quality']['grade'], 'D')
        self.assertIn('초안 없음', result['quality']['issues'])

    # --- execute: AI 교정 실패 시 원본 사용 ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    @patch('litellm.completion')
    def test_execute_edit_failure_uses_original(self, mock_llm, _):
        quality_json = json.dumps({
            "grade": "B", "readability": 7, "accuracy": 7,
            "issues": [], "summary": "보통"
        })
        mock_llm.side_effect = [
            Exception('AI 오류'),  # 교정 실패
            self._mock_completion(quality_json),  # 품질 평가
        ]

        agent = self._make_agent()
        result = agent.execute({'draft': '# 원본 초안\n내용', 'summary': '요약'})

        # 원본 초안이 그대로 사용됨
        self.assertIn('원본 초안', result['edited_content'])

    # --- _extract_title ---

    @patch('litellm.completion')
    def test_deep_long_edit_preserves_full_draft_when_provider_truncates(self, mock_llm):
        draft = '# 긴 초안\n' + ('본문 문장입니다.\n' * 15000) + '\n마지막 결론 문단'
        truncated = self._mock_completion('# 긴 초안\n중간에서 잘린 교정본')
        truncated.choices[0].finish_reason = 'length'
        quality = self._mock_completion('{"grade": "B"}')
        quality.choices[0].finish_reason = 'stop'
        mock_llm.side_effect = [truncated, quality]
        result = self._make_agent().execute({
            'draft': draft, 'detail_level': 'deep', 'modifiers': {'length': 'long'},
        })
        self.assertEqual(mock_llm.call_args_list[0].kwargs['max_tokens'], 32000)
        self.assertEqual(result['edited_content'], draft)
        self.assertTrue(result['edited_content'].endswith('마지막 결론 문단'))

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    def test_extract_title_from_h1(self, _):
        agent = self._make_agent()
        self.assertEqual(agent._extract_title('# 제목입니다\n본문'), '제목입니다')

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    def test_extract_title_no_h1(self, _):
        agent = self._make_agent()
        self.assertEqual(agent._extract_title('본문만 있는 텍스트'), 'AI 생성 콘텐츠')

    # --- _parse_json ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    def test_parse_json_invalid_returns_default(self, _):
        agent = self._make_agent()
        result = agent._parse_json('유효하지 않은 텍스트')
        self.assertEqual(result['grade'], 'B')

    # --- _evaluate_quality 실패 시 기본값 ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    @patch('litellm.completion', side_effect=Exception('평가 실패'))
    def test_evaluate_quality_failure_returns_default(self, mock_llm, _):
        agent = self._make_agent()
        result = agent._evaluate_quality('콘텐츠')
        self.assertEqual(result['grade'], 'B')
        self.assertEqual(result['readability'], 7)


if __name__ == '__main__':
    unittest.main()
