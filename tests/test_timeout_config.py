"""Phase 1: 타임아웃 300초 설정 검증"""
import unittest
from unittest.mock import patch


class TestTimeoutConfig(unittest.TestCase):
    """ai_service의 타임아웃이 300초로 설정되었는지 검증"""

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_completion_kwargs_timeout_is_300(self, _mock):
        from services.core.ai_service import _build_completion_kwargs

        kwargs = _build_completion_kwargs('gemini/gemini-3-flash-preview', 'test prompt')
        self.assertEqual(kwargs['timeout'], 300)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_glm_model_timeout_is_300(self, _mock):
        import os
        os.environ.setdefault('ZHIPUAI_API_KEY', 'test-key')
        from services.core.ai_service import _build_completion_kwargs

        kwargs = _build_completion_kwargs('zhipuai/GLM-4.7', 'test prompt')
        self.assertEqual(kwargs['timeout'], 300)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_deepseek_model_timeout_is_300(self, _mock):
        from services.core.ai_service import _build_completion_kwargs

        kwargs = _build_completion_kwargs('deepseek/deepseek-chat', 'test prompt')
        self.assertEqual(kwargs['timeout'], 300)


if __name__ == '__main__':
    unittest.main()
