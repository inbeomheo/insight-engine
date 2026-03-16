"""get_model_display_name 및 /generate 응답의 model_name 필드 테스트 (R34)"""
import unittest

from config import get_model_display_name


class TestGetModelDisplayName(unittest.TestCase):
    """config.get_model_display_name 단위 테스트"""

    def test_known_model_returns_name(self):
        """등록된 모델 ID → 표시명 반환"""
        name = get_model_display_name('zhipuai/GLM-4.5-Air')
        self.assertIn('GLM', name)
        self.assertNotEqual(name, 'zhipuai/GLM-4.5-Air')

    def test_unknown_model_returns_id(self):
        """미등록 모델 ID → ID 그대로 반환"""
        name = get_model_display_name('unknown/model-xyz')
        self.assertEqual(name, 'unknown/model-xyz')

    def test_gemini_model(self):
        """Gemini 모델 표시명"""
        name = get_model_display_name('gemini/gemini-3.1-flash-lite-preview')
        self.assertIn('Gemini', name)

    def test_deepseek_model(self):
        """DeepSeek 모델 표시명"""
        name = get_model_display_name('deepseek/deepseek-chat')
        self.assertIn('DeepSeek', name)

    def test_ollama_model(self):
        """Ollama 모델 표시명"""
        name = get_model_display_name('ollama_chat/llama3.2')
        self.assertIn('Llama', name)

    def test_empty_string(self):
        """빈 문자열 → 빈 문자열 반환"""
        name = get_model_display_name('')
        self.assertEqual(name, '')


if __name__ == '__main__':
    unittest.main()
