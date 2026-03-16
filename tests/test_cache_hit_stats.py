"""캐시 히트 응답에 통계 필드 포함 검증."""
import unittest
from unittest.mock import patch, MagicMock
import time

from app import create_app


class TestCacheHitStats(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.generation_helpers.get_usage_for_response', return_value={'remaining': 5})
    def test_cache_hit_includes_stats(self, _mock_usage, _mock_sb):
        """캐시 히트 응답에 char_count, word_count 포함."""
        from flask import g
        from routes.generation_helpers import _handle_cache_hit

        cached_data = {
            'title': '캐시 제목',
            'content': '캐시된 콘텐츠 텍스트입니다',
            'html': '<p>cached</p>',
        }

        with self.app.test_request_context():
            g.user_id = 'test-user'
            g.skip_usage_decrement = False
            self.app.ai_cache = MagicMock()
            self.app.ai_cache.get.return_value = cached_data

            resp = _handle_cache_hit(
                cache_key='test', force=False,
                youtube_title='Test', raw_transcript='tr',
                transcript_source='manual', start_time=time.time(),
            )

            self.assertIsNotNone(resp)
            data = resp.get_json()
            self.assertTrue(data['cached'])
            self.assertIn('char_count', data)
            self.assertIn('word_count', data)
            self.assertGreater(data['char_count'], 0)


if __name__ == '__main__':
    unittest.main()
