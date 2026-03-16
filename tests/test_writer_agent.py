"""
WriterAgent 단위 테스트
"""
import unittest
from unittest.mock import patch, MagicMock


class TestWriterAgent(unittest.TestCase):
    """services.agents.writer_agent.WriterAgent 테스트"""

    def _mock_completion(self, content: str):
        mock = MagicMock()
        mock.choices[0].message.content = content
        return mock

    def _make_agent(self):
        from services.agents.writer_agent import WriterAgent
        return WriterAgent(model='gemini/gemini-3-flash-preview')

    # --- 초기화 ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    def test_init_properties(self, _):
        agent = self._make_agent()
        self.assertEqual(agent.name, 'writer')
        self.assertEqual(agent.role, '콘텐츠 초안 작성')

    # --- execute: 정상 ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    @patch('litellm.completion')
    def test_execute_returns_draft(self, mock_llm, _):
        draft = '# AI 활용법\n\nAI를 활용하는 방법에 대한 초안입니다.'
        mock_llm.return_value = self._mock_completion(draft)

        agent = self._make_agent()
        result = agent.execute({
            'transcript': '자막 텍스트입니다.',
            'style_prompt': '블로그 형식',
            'main_topic': 'AI 활용',
            'key_points': ['포인트1', '포인트2'],
        })

        self.assertEqual(result['agent'], 'writer')
        self.assertIn('AI 활용법', result['draft'])
        self.assertEqual(result['title'], 'AI 활용법')

    # --- execute: AI 실패 ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    @patch('litellm.completion', side_effect=Exception('API 오류'))
    def test_execute_failure_raises(self, mock_llm, _):
        agent = self._make_agent()
        with self.assertRaises(Exception):
            agent.execute({'transcript': '자막'})

    # --- execute: 모디파이어 ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    @patch('litellm.completion')
    def test_execute_with_length_modifier(self, mock_llm, _):
        mock_llm.return_value = self._mock_completion('# 제목\n본문')

        agent = self._make_agent()
        result = agent.execute({
            'transcript': '자막',
            'modifiers': {'length': 'short'},
        })

        self.assertEqual(result['agent'], 'writer')
        # max_tokens가 LENGTH_MAX_TOKENS['short'] 값 사용되었는지 확인
        kwargs = mock_llm.call_args[1]
        from config import LENGTH_MAX_TOKENS
        self.assertEqual(kwargs['max_tokens'], LENGTH_MAX_TOKENS.get('short', 4000))

    # --- execute: 웹 컨텍스트 포함 ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    @patch('litellm.completion')
    def test_execute_with_web_context(self, mock_llm, _):
        mock_llm.return_value = self._mock_completion('# 제목\n내용')

        agent = self._make_agent()
        result = agent.execute({
            'transcript': '자막',
            'web_context': '웹 검색 결과 참고자료',
        })

        # 프롬프트에 웹 컨텍스트가 포함되었는지 확인
        call_args = mock_llm.call_args
        prompt_content = call_args[1]['messages'][0]['content']
        self.assertIn('웹 검색 참고자료', prompt_content)

    # --- _extract_title ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    def test_extract_title(self, _):
        agent = self._make_agent()
        self.assertEqual(agent._extract_title('# 멋진 제목\n본문'), '멋진 제목')
        self.assertEqual(agent._extract_title('본문만'), 'AI 생성 콘텐츠')

    # --- execute: 자막 길이 제한 ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    @patch('litellm.completion')
    def test_execute_truncates_long_transcript(self, mock_llm, _):
        mock_llm.return_value = self._mock_completion('# 제목\n본문')

        agent = self._make_agent()
        long_transcript = 'x' * 20000
        agent.execute({'transcript': long_transcript})

        call_args = mock_llm.call_args
        prompt_content = call_args[1]['messages'][0]['content']
        # 자막이 8000자로 잘림 (프롬프트 전체 길이가 원본보다 짧아야 함)
        self.assertLess(len(prompt_content), 20000)


if __name__ == '__main__':
    unittest.main()
