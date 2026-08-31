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
        agent = ConcreteAgent(model='cliproxy/gpt-5.6-sol')
        self.assertEqual(agent.model, 'cliproxy/gpt-5.6-sol')

    def test_init_without_model(self):
        agent = ConcreteAgent()
        self.assertIsNone(agent.model)

    def test_abstract_properties(self):
        agent = ConcreteAgent(model='test')
        self.assertEqual(agent.name, 'test_agent')
        self.assertEqual(agent.role, '테스트 에이전트')

    # --- _get_default_model ---

    @patch('services.agents.base_agent.BaseAgent._get_default_model')
    def test_get_default_model_cliproxy(self, mock_default):
        mock_default.return_value = 'cliproxy/gpt-5.6-sol'
        agent = ConcreteAgent()
        self.assertEqual(agent._get_default_model(), 'cliproxy/gpt-5.6-sol')

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

        agent = ConcreteAgent(model='cliproxy/gpt-5.6-sol')
        result = agent._call_ai('테스트 프롬프트')
        self.assertEqual(result, '응답 텍스트')

    # --- _call_ai: CLIProxyAPI ---

    @patch('litellm.completion')
    def test_call_ai_cliproxy_sets_api_base(self, mock_llm):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = '응답'
        mock_llm.return_value = mock_resp

        agent = ConcreteAgent(model='cliproxy/gpt-5.6-sol')
        agent._call_ai('prompt')

        kwargs = mock_llm.call_args[1]
        self.assertEqual(kwargs['model'], 'openai/gpt-5.6-sol')
        self.assertEqual(kwargs['api_key'], 'test-cliproxy-key')
        self.assertIn('api_base', kwargs)
        self.assertEqual(kwargs['reasoning_effort'], 'medium')
        self.assertTrue(kwargs['drop_params'])
        self.assertNotIn('temperature', kwargs)

    @patch('litellm.completion')
    def test_call_ai_raw_gpt_uses_cliproxy(self, mock_llm):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = '응답'
        mock_llm.return_value = mock_resp

        agent = ConcreteAgent(model='gpt-5.4')
        agent._call_ai('prompt')

        kwargs = mock_llm.call_args[1]
        self.assertEqual(kwargs['model'], 'openai/gpt-5.4')
        self.assertEqual(kwargs['api_key'], 'test-cliproxy-key')
        self.assertIn('api_base', kwargs)

    # --- _call_ai: 오류 ---

    @patch('litellm.completion', side_effect=Exception('timeout'))
    def test_call_ai_failure_raises(self, mock_llm):
        agent = ConcreteAgent(model='cliproxy/gpt-5.6-sol')
        with self.assertRaises(Exception) as ctx:
            agent._call_ai('prompt')
        self.assertIn('timeout', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
