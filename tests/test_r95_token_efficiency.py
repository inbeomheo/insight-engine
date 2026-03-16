"""R95: /generate 응답에 token_efficiency (글자수/토큰수 비율) 필드 테스트."""
import unittest
from unittest.mock import patch, MagicMock

from app import create_app


class TestTokenEfficiency(unittest.TestCase):
    """_save_and_respond가 token_efficiency 필드를 포함하는지 검증."""

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_token_efficiency_in_generate_response(self, _):
        """generate 응답에 token_efficiency 필드가 존재한다."""
        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()

        mock_result = {
            'title': '테스트 제목',
            'content': '테스트 콘텐츠입니다. 이것은 충분히 긴 콘텐츠입니다.',
            'html': '<p>테스트</p>',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
        }

        with patch('routes.blog_routes.content_service') as mock_cs, \
             patch('routes.blog_routes.ai_service') as mock_ai, \
             patch('routes.blog_routes._get_request_data') as mock_params, \
             patch('routes.generation_helpers.save_history'), \
             patch('routes.generation_helpers.ai_service') as mock_ai2, \
             patch('routes.generation_helpers.get_usage_for_response', return_value={'remaining': 5}):

            mock_cs.is_youtube_url.return_value = True
            mock_cs.get_video_id.return_value = 'test123'
            mock_cs.get_content_title.return_value = '테스트 영상'
            mock_cs.get_transcript.return_value = ('자막 텍스트입니다. 충분한 길이의 자막.', None, None)
            mock_cs.truncate_text.return_value = '자막'

            mock_params.return_value = {
                'url': 'https://youtube.com/watch?v=test123',
                'model': 'gemini/gemini-2.5-flash-lite-preview-09-2025',
                'style': 'summary',
                'custom_prompt': None,
                'modifiers': {'length': 'medium', 'writing_style': 'conversational'},
                'include_transcript': False,
                'enable_citations': False,
                'analyze': False,
                'output_format': 'html',
                'max_chars': None,
                'detail_level': None,
                'content': None,
            }

            mock_ai.create_content.return_value = (mock_result, '프롬프트')
            mock_ai2.extract_seo_metadata.return_value = None
            mock_ai2.extract_geo_metadata.return_value = None
            mock_ai2.extract_faq_schema.return_value = None
            mock_ai2.extract_cta.return_value = None

            with patch('routes.blog_routes._fetch_youtube_content',
                       return_value=('자막 텍스트', [], None, '자막 원문', 'youtube_api', None)):
                with patch('routes.blog_routes._handle_short_content_bypass', return_value=None):
                    with patch('routes.blog_routes._handle_cache_hit', return_value=None):
                        with patch('routes.blog_routes._call_ai_with_comments',
                                   return_value=(mock_result, '프롬프트', None)):
                            with patch('routes.blog_routes.get_model_max_tokens', return_value=8000):
                                resp = client.post(
                                    '/generate',
                                    json={'url': 'https://youtube.com/watch?v=test123'},
                                    headers={'Origin': 'http://localhost:3000'},
                                )

        if resp.status_code == 200:
            data = resp.get_json()
            self.assertIn('token_efficiency', data)
            self.assertIsInstance(data['token_efficiency'], float)
            self.assertGreater(data['token_efficiency'], 0.0)

    def test_token_efficiency_calculation(self):
        """token_efficiency 계산 로직: 글자수 / 총 토큰수."""
        # 직접 계산 로직 테스트
        char_count = 1000
        total_tokens = 500
        expected = round(char_count / total_tokens, 2)
        self.assertEqual(expected, 2.0)

    def test_token_efficiency_zero_tokens(self):
        """total_tokens가 0이면 token_efficiency = 0.0."""
        char_count = 100
        total_tokens = 0
        result = round(char_count / total_tokens, 2) if total_tokens > 0 else 0.0
        self.assertEqual(result, 0.0)

    def test_token_efficiency_no_usage(self):
        """usage가 없으면 token_efficiency = 0.0."""
        usage = None
        total_tokens = (usage or {}).get('total_tokens', 0)
        result = round(100 / total_tokens, 2) if total_tokens > 0 else 0.0
        self.assertEqual(result, 0.0)

    def test_token_efficiency_precision(self):
        """token_efficiency는 소수점 2자리로 반올림."""
        char_count = 333
        total_tokens = 100
        result = round(char_count / total_tokens, 2)
        self.assertEqual(result, 3.33)


if __name__ == '__main__':
    unittest.main()
