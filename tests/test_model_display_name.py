"""get_model_display_name 및 /generate 응답의 model_name 필드 테스트 (R34)"""
import unittest

from config import get_model_display_name


class TestGetModelDisplayName(unittest.TestCase):
    """config.get_model_display_name 단위 테스트"""

    def test_known_model_returns_name(self):
        """등록된 모델 ID → 표시명 반환"""
        name = get_model_display_name('chatmock/gpt-5.3-codex-spark')
        self.assertIn('GPT', name)
        self.assertNotEqual(name, 'chatmock/gpt-5.3-codex-spark')

    def test_unknown_model_returns_id(self):
        """미등록 모델 ID → ID 그대로 반환"""
        name = get_model_display_name('unknown/model-xyz')
        self.assertEqual(name, 'unknown/model-xyz')

    def test_legacy_chatmock_model_is_not_registered(self):
        """배포에서 제거한 ChatMock 모델은 다시 노출하지 않는다."""
        name = get_model_display_name('chatmock/gpt-5.4')
        self.assertEqual(name, 'chatmock/gpt-5.4')

    def test_empty_string(self):
        """빈 문자열 → 빈 문자열 반환"""
        name = get_model_display_name('')
        self.assertEqual(name, '')


if __name__ == '__main__':
    unittest.main()
