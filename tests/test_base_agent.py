"""
base_agent (콘텐츠 파이프라인 베이스) 단위 테스트
"""
import unittest
from unittest.mock import patch, MagicMock

from services.agents.base_agent import BaseAgent
from services.usage.usage_lock import UsageLockUnavailable


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
        agent = ConcreteAgent(model='cliproxyapi/gpt-5.5')
        self.assertEqual(agent.model, 'cliproxyapi/gpt-5.5')

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
        mock_default.return_value = 'cliproxyapi/gpt-5.5'
        agent = ConcreteAgent()
        self.assertEqual(agent._get_default_model(), 'cliproxyapi/gpt-5.5')

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

        agent = ConcreteAgent(model='cliproxyapi/gpt-5.5')
        result = agent._call_ai('테스트 프롬프트')
        self.assertEqual(result, '응답 텍스트')

    # --- _call_ai: ChatMock ---

    @patch('litellm.completion')
    def test_call_ai_chatmock_sets_api_base(self, mock_llm):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = '응답'
        mock_llm.return_value = mock_resp

        agent = ConcreteAgent(model='cliproxyapi/gpt-5.5')
        agent._call_ai('prompt')

        kwargs = mock_llm.call_args[1]
        self.assertEqual(kwargs['model'], 'gpt-5.5')
        self.assertEqual(kwargs['api_key'], 'test-gateway-key')
        self.assertIn('api_base', kwargs)
        self.assertEqual(kwargs['reasoning_effort'], 'medium')
        self.assertTrue(kwargs['drop_params'])
        self.assertNotIn('temperature', kwargs)

    @patch('litellm.completion')
    def test_call_ai_raw_gpt_uses_chatmock(self, mock_llm):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = '응답'
        mock_llm.return_value = mock_resp

        agent = ConcreteAgent(model='gpt-5.5')
        agent._call_ai('prompt')

        kwargs = mock_llm.call_args[1]
        self.assertEqual(kwargs['model'], 'gpt-5.5')
        self.assertEqual(kwargs['api_key'], 'test-gateway-key')
        self.assertIn('api_base', kwargs)

    # --- _call_ai: 오류 ---

    @patch('litellm.completion')
    def test_call_ai_rejects_truncated_response(self, mock_llm):
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = '잘린 본문'
        mock_resp.choices[0].finish_reason = 'length'
        mock_llm.return_value = mock_resp
        agent = ConcreteAgent(model='cliproxyapi/gpt-5.5')
        with self.assertRaisesRegex(RuntimeError, '출력 길이 제한'):
            agent._call_ai('prompt')

    @patch('services.usage.usage_decorator.mark_usage_charge_committed')
    @patch('litellm.completion')
    def test_call_ai_failure_raises_after_charge_commit(self, mock_llm, mock_mark):
        def fail_after_provider_start(**_kwargs):
            self.assertTrue(mock_mark.called)
            raise Exception('timeout')

        mock_llm.side_effect = fail_after_provider_start
        agent = ConcreteAgent(model='cliproxyapi/gpt-5.5')
        with self.assertRaises(Exception) as ctx:
            agent._call_ai('prompt')
        self.assertIn('timeout', str(ctx.exception))
        mock_mark.assert_called_once_with()

    @patch('litellm.completion')
    def test_call_ai_uses_trusted_callback_at_provider_boundary(self, mock_llm):
        callback = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = '응답'

        def complete_after_callback(**_kwargs):
            callback.assert_called_once_with()
            return mock_resp

        mock_llm.side_effect = complete_after_callback
        agent = ConcreteAgent(
            model='cliproxyapi/gpt-5.5',
            on_cost_start=callback,
        )

        self.assertEqual(agent._call_ai('prompt'), '응답')

    @patch('litellm.completion')
    def test_call_ai_lock_loss_stops_provider_and_preserves_exception(self, mock_llm):
        callback = MagicMock(side_effect=UsageLockUnavailable('lease lost'))
        agent = ConcreteAgent(
            model='cliproxyapi/gpt-5.5',
            on_cost_start=callback,
        )

        with self.assertRaises(UsageLockUnavailable):
            agent._call_ai('prompt')

        callback.assert_called_once_with()
        mock_llm.assert_not_called()


if __name__ == '__main__':
    unittest.main()
