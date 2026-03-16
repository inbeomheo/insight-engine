"""R15: rewrite 응답에 compression_ratio 포함 테스트"""
import unittest
from unittest.mock import patch


class TestRewriteCompressionRatio(unittest.TestCase):
    """rewrite_for_platform 응답의 compression_ratio 필드 검증"""

    @patch('services.content.rewrite_service.ai_service')
    def test_compression_ratio_present(self, mock_ai):
        """응답에 compression_ratio 필드가 존재하는지 확인"""
        mock_ai.create_content.return_value = {'content': '짧은 결과'}

        from services.content.rewrite_service import rewrite_for_platform
        result = rewrite_for_platform('원본 콘텐츠 텍스트입니다. 충분히 긴 내용.', 'twitter', 'test-model')

        self.assertIn('compression_ratio', result)

    @patch('services.content.rewrite_service.ai_service')
    def test_compression_ratio_calculation(self, mock_ai):
        """compression_ratio가 올바르게 계산되는지 확인"""
        original = 'A' * 1000
        rewritten = 'B' * 200
        mock_ai.create_content.return_value = {'content': rewritten}

        from services.content.rewrite_service import rewrite_for_platform
        result = rewrite_for_platform(original, 'twitter', 'test-model')

        # 200 / 1000 = 0.2
        self.assertAlmostEqual(result['compression_ratio'], 0.2, places=2)

    @patch('services.content.rewrite_service.ai_service')
    def test_compression_ratio_with_empty_original(self, mock_ai):
        """빈 원본일 때 compression_ratio가 0.0"""
        mock_ai.create_content.return_value = {'content': '결과'}

        from services.content.rewrite_service import rewrite_for_platform
        result = rewrite_for_platform('', 'twitter', 'test-model')

        self.assertEqual(result['compression_ratio'], 0.0)

    def test_unsupported_platform_no_ratio(self):
        """지원하지 않는 플랫폼은 에러 반환 (compression_ratio 없음)"""
        from services.content.rewrite_service import rewrite_for_platform
        result = rewrite_for_platform('내용', 'invalid_platform', 'test-model')

        self.assertIn('error', result)
        self.assertNotIn('compression_ratio', result)

    @patch('services.content.rewrite_service.ai_service')
    def test_existing_fields_preserved(self, mock_ai):
        """기존 필드(platform, text, char_count, max_chars)가 유지되는지 확인"""
        mock_ai.create_content.return_value = {'content': '트위터 변환 결과'}

        from services.content.rewrite_service import rewrite_for_platform
        result = rewrite_for_platform('원본 텍스트', 'twitter', 'test-model')

        self.assertIn('platform', result)
        self.assertIn('text', result)
        self.assertIn('char_count', result)
        self.assertIn('max_chars', result)
        self.assertIn('compression_ratio', result)


if __name__ == '__main__':
    unittest.main()
