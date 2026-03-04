"""Phase 3: 프로바이더별 실제 API 호출 검증

주의: 실제 API 크레딧을 소모합니다. 필요할 때만 실행하세요.
실행: pytest tests/test_provider_live.py -v
"""
import os
import unittest
from unittest.mock import patch
from dotenv import load_dotenv

load_dotenv()

SHORT_PROMPT = '다음 자막을 2줄로 요약해주세요:\n\n안녕하세요. 오늘은 파이썬 기초를 배워보겠습니다. 변수와 함수를 알아봅시다.'


@patch('services.supabase_service.is_supabase_enabled', return_value=False)
class TestProviderLive(unittest.TestCase):
    """각 프로바이더의 실제 API 호출 테스트"""

    @classmethod
    def setUpClass(cls):
        from app import app
        cls.app = app
        cls.ctx = app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def test_glm_47(self, _mock):
        """GLM-4.7 실제 호출"""
        if not os.getenv('ZHIPUAI_API_KEY'):
            self.skipTest('ZHIPUAI_API_KEY 없음')

        from services.ai_service import create_content
        result = create_content(
            SHORT_PROMPT,
            model='zhipuai/GLM-4.7',
            style_id='summary',
            modifiers={'length': 'short'},
        )
        self.assertIn('content', result)
        self.assertTrue(len(result['content']) > 10, '응답이 너무 짧음')
        print(f"  GLM-4.7: {len(result['content'])}자, {result.get('usage', {}).get('total_tokens', '?')} tokens")

    def test_glm_45_air(self, _mock):
        """GLM-4.5-Air 실제 호출"""
        if not os.getenv('ZHIPUAI_API_KEY'):
            self.skipTest('ZHIPUAI_API_KEY 없음')

        from services.ai_service import create_content
        result = create_content(
            SHORT_PROMPT,
            model='zhipuai/GLM-4.5-Air',
            style_id='summary',
            modifiers={'length': 'short'},
        )
        self.assertIn('content', result)
        self.assertTrue(len(result['content']) > 10, '응답이 너무 짧음')
        print(f"  GLM-4.5-Air: {len(result['content'])}자, {result.get('usage', {}).get('total_tokens', '?')} tokens")

    def test_deepseek_chat(self, _mock):
        """DeepSeek Chat 실제 호출"""
        if not os.getenv('DEEPSEEK_API_KEY'):
            self.skipTest('DEEPSEEK_API_KEY 없음')

        from services.ai_service import create_content
        result = create_content(
            SHORT_PROMPT,
            model='deepseek/deepseek-chat',
            style_id='summary',
            modifiers={'length': 'short'},
        )
        self.assertIn('content', result)
        self.assertTrue(len(result['content']) > 10, '응답이 너무 짧음')
        print(f"  DeepSeek Chat: {len(result['content'])}자, {result.get('usage', {}).get('total_tokens', '?')} tokens")

    def test_deepseek_reasoner(self, _mock):
        """DeepSeek Reasoner 실제 호출"""
        if not os.getenv('DEEPSEEK_API_KEY'):
            self.skipTest('DEEPSEEK_API_KEY 없음')

        from services.ai_service import create_content
        result = create_content(
            SHORT_PROMPT,
            model='deepseek/deepseek-reasoner',
            style_id='summary',
            modifiers={'length': 'short'},
        )
        self.assertIn('content', result)
        self.assertTrue(len(result['content']) > 10, '응답이 너무 짧음')
        print(f"  DeepSeek Reasoner: {len(result['content'])}자, {result.get('usage', {}).get('total_tokens', '?')} tokens")


if __name__ == '__main__':
    unittest.main()
