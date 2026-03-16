"""R70: /api/content/stats 응답에 unique_words (중복 제거 단어 수) 포함 검증."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestContentStatsUniqueWords(unittest.TestCase):
    """콘텐츠 통계의 unique_words 필드 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_unique_words_field_present(self, _mock_sb):
        """unique_words 필드가 응답에 포함되어야 함."""
        resp = self.client.post('/api/content/stats',
                                json={'content': '안녕하세요 세계 안녕하세요'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('unique_words', data)
        self.assertIsInstance(data['unique_words'], int)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_unique_words_deduplicates(self, _mock_sb):
        """중복 단어는 1회만 카운트."""
        resp = self.client.post('/api/content/stats',
                                json={'content': 'hello world hello world hello'},
                                headers=_HEADERS)
        data = resp.get_json()
        self.assertEqual(data['word_count'], 5)
        self.assertEqual(data['unique_words'], 2)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_unique_words_case_insensitive(self, _mock_sb):
        """대소문자 무시하여 중복 제거."""
        resp = self.client.post('/api/content/stats',
                                json={'content': 'Hello HELLO hello World'},
                                headers=_HEADERS)
        data = resp.get_json()
        self.assertEqual(data['unique_words'], 2)


if __name__ == '__main__':
    unittest.main()
