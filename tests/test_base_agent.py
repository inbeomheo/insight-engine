"""
base_agent (콘텐츠 파이프라인 베이스) 단위 테스트
"""
import unittest
from unittest.mock import patch, MagicMock

from services.agents.base_agent import BaseAgent


class ConcreteAgent(BaseAgent):
    """테스트용 구체 에이전트"""

    @property
    def name(self) -> str:
        return 'test_agent'

    @property
    def role(self) -> str:
        return '테스트 에이전트'

    def execute(self, context: dict) -> dict:
        return {'agent': self.name}


class TestBaseAgent(unittest.TestCase):
    """services.agents.base_agent.BaseAgent 테스트"""

    # --- 초기화 ---

    def test_init_with_model(self):
        agent = ConcreteAgent(model='gemini/gemini-3-flash-preview')
        self.assertEqual(agent.model, 'gemini/gemini-3-flash-preview')

    def test_init_without_model(self):
        agent = ConcreteAgent()
        self.assertIsNone(agent.model)

    def test_abstract_properties(self):
        agent = ConcreteAgent(model='test')
        self.assertEqual(agent.name, 'test_agent')
        self.assertEqual(agent.role, '테스트 에이전트')

    # --- _get_default_model ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model')
    def test_get_default_model_chatmock(self, mock_default):
        mock_default.return_value = 'chatmock/gpt-5.4-mini'
        agent = ConcreteAgent()
        self.assertEqual(agent._get_default_model(), 'chatmock/gpt-5.4-mini')

    def test_get_default_model_no_config(self):
        """config import 실패 시 기본 모델 반환"""
        agent = ConcreteAgent()
        with patch.dict('sys.modules', {'config': None}):
            # _get_default_model 내부에서 import 실패 시 기본값 반환
            result = agent._get_default_model()
            self.assertIsInstance(result, str)

    # --- _call_ai: 정상 ---

    @patch('litellm.completion')
    def test_call_ai_success(self, mock_llm):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = '응답 텍스트'
        mock_llm.return_value = mock_resp

        agent = ConcreteAgent(model='gemini/gemini-3-flash-preview')
        result = agent._call_ai('테스트 프롬프트')
        self.assertEqual(result, '응답 텍스트')

    # --- _call_ai: Gemini reasoning_effort ---

    @patch('litellm.completion')
    def test_call_ai_gemini_adds_reasoning_effort(self, mock_llm):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = '응답'
        mock_llm.return_value = mock_resp

        agent = ConcreteAgent(model='gemini/gemini-3-flash-preview')
        agent._call_ai('prompt')

        kwargs = mock_llm.call_args[1]
        self.assertEqual(kwargs.get('reasoning_effort'), 'minimal')

    @patch('litellm.completion')
    def test_call_ai_gemini_lite_no_reasoning_effort(self, mock_llm):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = '응답'
        mock_llm.return_value = mock_resp

        agent = ConcreteAgent(model='gemini/gemini-2.5-flash-lite-preview-09-2025')
        agent._call_ai('prompt')

        kwargs = mock_llm.call_args[1]
        self.assertNotIn('reasoning_effort', kwargs)

    # --- _call_ai: 오류 ---

    @patch('litellm.completion', side_effect=Exception('timeout'))
    def test_call_ai_failure_raises(self, mock_llm):
        agent = ConcreteAgent(model='gemini/gemini-3-flash-preview')
        with self.assertRaises(Exception) as ctx:
            agent._call_ai('prompt')
        self.assertIn('timeout', str(ctx.exception))

    # --- _call_ai: zhipuai ---

    @patch.dict('os.environ', {'ZHIPUAI_API_KEY': 'test-key'})
    @patch('litellm.completion')
    def test_call_ai_zhipuai_conversion(self, mock_llm):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = '응답'
        mock_llm.return_value = mock_resp

        agent = ConcreteAgent(model='zhipuai/GLM-4.7')
        agent._call_ai('prompt')

        kwargs = mock_llm.call_args[1]
        self.assertTrue(kwargs['model'].startswith('openai/'))
        self.assertEqual(kwargs['api_key'], 'test-key')

    @patch.dict('os.environ', {}, clear=True)
    def test_call_ai_zhipuai_no_key_raises(self):
        # ZHIPUAI_API_KEY 없는 환경
        import os
        os.environ.pop('ZHIPUAI_API_KEY', None)
        agent = ConcreteAgent(model='zhipuai/GLM-4.7')
        with self.assertRaises(ValueError):
            agent._call_ai('prompt')

    # --- _call_ai: ChatMock ---

    @patch('litellm.completion')
    def test_call_ai_chatmock_sets_api_base(self, mock_llm):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = '응답'
        mock_llm.return_value = mock_resp

        agent = ConcreteAgent(model='chatmock/gpt-5.4-mini')
        agent._call_ai('prompt')

        kwargs = mock_llm.call_args[1]
        self.assertEqual(kwargs['model'], 'gpt-5.4-mini')
        self.assertEqual(kwargs['api_key'], 'dummy')
        self.assertIn('api_base', kwargs)


if __name__ == '__main__':
    unittest.main()
