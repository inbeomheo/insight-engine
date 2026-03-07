"""rewrite_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services import rewrite_service


MOCK_PRESETS = {
    'twitter': {'max_chars': 280, 'tone': '간결하고 임팩트 있게', 'format': '짧은 문장'},
    'linkedin': {'max_chars': 3000, 'tone': '전문적', 'format': '단락'},
}


class TestRewriteForPlatform(unittest.TestCase):
    """플랫폼별 카피 변환 테스트"""

    @patch.object(rewrite_service, 'PLATFORM_PRESETS', MOCK_PRESETS)
    @patch.object(rewrite_service, 'ai_service')
    def test_success(self, mock_ai):
        """정상 변환"""
        mock_ai.create_content.return_value = {'content': '변환된 텍스트'}
        result = rewrite_service.rewrite_for_platform('원본', 'twitter', 'model1')
        self.assertEqual(result['platform'], 'twitter')
        self.assertEqual(result['text'], '변환된 텍스트')
        self.assertEqual(result['char_count'], len('변환된 텍스트'))

    @patch.object(rewrite_service, 'PLATFORM_PRESETS', MOCK_PRESETS)
    def test_unsupported_platform(self):
        """지원하지 않는 플랫폼"""
        result = rewrite_service.rewrite_for_platform('원본', 'tiktok', 'model1')
        self.assertIn('error', result)

    @patch.object(rewrite_service, 'PLATFORM_PRESETS', MOCK_PRESETS)
    @patch.object(rewrite_service, 'ai_service')
    def test_truncate_over_max_chars(self, mock_ai):
        """max_chars 초과 시 잘림"""
        mock_ai.create_content.return_value = {'content': 'A' * 300}
        result = rewrite_service.rewrite_for_platform('원본', 'twitter', 'model1')
        self.assertLessEqual(len(result['text']), 280)
        self.assertTrue(result['text'].endswith('...'))

    @patch.object(rewrite_service, 'PLATFORM_PRESETS', MOCK_PRESETS)
    @patch.object(rewrite_service, 'ai_service')
    def test_within_max_chars(self, mock_ai):
        """max_chars 이내면 그대로"""
        mock_ai.create_content.return_value = {'content': '짧은 텍스트'}
        result = rewrite_service.rewrite_for_platform('원본', 'twitter', 'model1')
        self.assertEqual(result['text'], '짧은 텍스트')

    @patch.object(rewrite_service, 'PLATFORM_PRESETS', MOCK_PRESETS)
    @patch.object(rewrite_service, 'ai_service')
    def test_empty_content_from_ai(self, mock_ai):
        """AI가 빈 결과 반환"""
        mock_ai.create_content.return_value = {'content': ''}
        result = rewrite_service.rewrite_for_platform('원본', 'twitter', 'model1')
        self.assertEqual(result['text'], '')
        self.assertEqual(result['char_count'], 0)

    @patch.object(rewrite_service, 'PLATFORM_PRESETS', MOCK_PRESETS)
    @patch.object(rewrite_service, 'ai_service')
    def test_max_chars_in_result(self, mock_ai):
        """결과에 max_chars 포함"""
        mock_ai.create_content.return_value = {'content': 'ok'}
        result = rewrite_service.rewrite_for_platform('원본', 'twitter', 'model1')
        self.assertEqual(result['max_chars'], 280)

    @patch.object(rewrite_service, 'PLATFORM_PRESETS', MOCK_PRESETS)
    @patch.object(rewrite_service, 'ai_service')
    def test_content_truncated_to_3000(self, mock_ai):
        """원본 콘텐츠가 3000자로 잘려서 프롬프트에 포함"""
        mock_ai.create_content.return_value = {'content': 'result'}
        long_content = 'X' * 5000
        rewrite_service.rewrite_for_platform(long_content, 'linkedin', 'model1')
        call_args = mock_ai.create_content.call_args
        prompt = call_args[0][0]
        # 원본 5000자가 3000자로 잘림
        self.assertNotIn('X' * 5000, prompt)


if __name__ == '__main__':
    unittest.main()
