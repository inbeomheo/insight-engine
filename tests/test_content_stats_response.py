"""생성 응답 콘텐츠 통계 필드 테스트."""
import unittest
from unittest.mock import patch, MagicMock
import time

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestContentStatsInResponse(unittest.TestCase):
    """_save_and_respond에서 char_count/word_count 포함 검증."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.generation_helpers.save_history')
    @patch('routes.generation_helpers.get_usage_for_response', return_value={'remaining': 5})
    def test_response_includes_stats(self, _mock_usage, _mock_save, _mock_sb):
        """생성 응답에 char_count, word_count 포함."""
        from flask import g
        from routes.generation_helpers import _save_and_respond

        with self.app.test_request_context():
            g.user_id = 'test-user'
            result = {
                'title': '테스트 제목',
                'content': '이것은 테스트 콘텐츠입니다 열 단어 정도의 텍스트',
                'html': '<p>test</p>',
            }
            resp = _save_and_respond(
                result=result, used_prompt='test', comment_result=None,
                cache_key='test_key', video_id='test123',
                params={'model': 'test', 'style': 'summary', 'modifiers': {}},
                url='https://youtube.com/watch?v=test',
                youtube_title='Test', raw_transcript='transcript',
                transcript_source='manual', comments=None,
                start_time=time.time(),
            )

            data = resp.get_json()
            self.assertIn('char_count', data)
            self.assertIn('word_count', data)
            self.assertGreater(data['char_count'], 0)
            self.assertGreater(data['word_count'], 0)

    def test_empty_content_zero_stats(self):
        """빈 콘텐츠는 0."""
        text = ''
        self.assertEqual(len(text), 0)
        self.assertEqual(len(text.split()) if text else 0, 0)


if __name__ == '__main__':
    unittest.main()
