"""콘텐츠 통계 분석 API 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestContentStats(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_returns_all_fields(self, _mock_sb):
        """모든 통계 필드 반환."""
        resp = self.client.post('/api/content/stats',
                                json={'content': '안녕하세요. 테스트 문장입니다. 세 번째 문장.'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        for field in ['char_count', 'word_count', 'sentence_count', 'reading_time_min', 'avg_sentence_length']:
            self.assertIn(field, data)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_empty_content_returns_400(self, _mock_sb):
        """빈 콘텐츠는 400."""
        resp = self.client.post('/api/content/stats',
                                json={'content': ''},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_reading_time_minimum_1(self, _mock_sb):
        """읽기 시간은 최소 1분."""
        resp = self.client.post('/api/content/stats',
                                json={'content': '짧은 글'},
                                headers=_HEADERS)
        data = resp.get_json()
        self.assertGreaterEqual(data['reading_time_min'], 1)


if __name__ == '__main__':
    unittest.main()
