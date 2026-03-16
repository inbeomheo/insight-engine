"""R85: /api/rewrite 응답에 hashtag_count 필드 추가 테스트."""
import unittest
from services.content.rewrite_service import rewrite_for_platform


class TestHashtagCount(unittest.TestCase):

    def test_hashtag_count_in_result(self):
        """rewrite_for_platform 결과에 hashtag_count가 포함된다."""
        # 실제 AI 호출 없이 함수 로직만 테스트하기 위해 mock 사용
        from unittest.mock import patch
        mock_result = {'content': '멋진 콘텐츠입니다 #AI #테크 #개발'}
        with patch('services.content.rewrite_service.ai_service.create_content', return_value=mock_result):
            result = rewrite_for_platform('원본 콘텐츠 텍스트입니다. 충분히 긴 텍스트.', 'twitter', 'gemini/gemini-3-flash-preview')
        self.assertNotIn('error', result)
        self.assertIn('hashtag_count', result)
        self.assertEqual(result['hashtag_count'], 3)

    def test_hashtag_count_zero(self):
        """해시태그가 없으면 0을 반환한다."""
        from unittest.mock import patch
        mock_result = {'content': '해시태그 없는 콘텐츠입니다.'}
        with patch('services.content.rewrite_service.ai_service.create_content', return_value=mock_result):
            result = rewrite_for_platform('원본 콘텐츠 텍스트입니다. 충분히 긴 텍스트.', 'twitter', 'gemini/gemini-3-flash-preview')
        self.assertEqual(result['hashtag_count'], 0)

    def test_unsupported_platform_no_hashtag_count(self):
        """지원하지 않는 플랫폼이면 error 반환, hashtag_count 없음."""
        result = rewrite_for_platform('텍스트', 'nonexistent_platform', 'model')
        self.assertIn('error', result)
        self.assertNotIn('hashtag_count', result)


if __name__ == '__main__':
    unittest.main()
